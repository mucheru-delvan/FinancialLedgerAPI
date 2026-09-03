from django.db.models import Q

from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from accounts.models import Account
from transactions.models import Transaction
from transactions.services import transfer_money
from transactions.serializers import (
    TransferSerializer,
    TransactionSerializer,
    TransactionFilterSerializer,
)


class TransferView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=TransferSerializer,
        responses={200: TransactionSerializer},
        tags=["transactions"],
    )
    def post(self, request):
        serializer = TransferSerializer(data=request.data)

        if serializer.is_valid():
            try:
                sender_account = Account.objects.filter(
                    pk=serializer.validated_data["from_account_id"],
                    user=request.user,
                    status="active",
                ).first()

                if not sender_account:
                    return Response(
                        {"detail": "You are not authorized to use this account."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                transfer = transfer_money(
                    from_account_id=sender_account.pk,
                    to_account_id=serializer.validated_data[
                        "to_account_id"
                    ],
                    amount=serializer.validated_data["amount"],
                    idempotency_key=serializer.validated_data[
                        "idempotency_key"
                    ],
                )

                return Response(
                    TransactionSerializer(transfer).data,
                    status=status.HTTP_200_OK,
                )

            except ValueError as error:
                return Response(
                    {"detail": str(error)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class TransactionListView(ListAPIView):

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[TransactionFilterSerializer],
        responses={200: TransactionSerializer(many=True)},
        tags=["transactions"],
    )
    def get_queryset(self):
        accounts = Account.objects.filter(
            user=self.request.user
        )

        filter_serializer = TransactionFilterSerializer(
            data=self.request.query_params
        )

        filter_serializer.is_valid(
            raise_exception=True
        )

        filters = filter_serializer.validated_data

        queryset = Transaction.objects.filter(
            Q(from_account__in=accounts)
            | Q(to_account__in=accounts)
        )

        status_filter = filters.get("status")

        if status_filter:
            queryset = queryset.filter(
                status=status_filter.upper()
            )

        direction = filters.get("direction")

        if direction:
            direction = direction.lower()

            if direction == "sent":
                queryset = queryset.filter(
                    from_account__in=accounts
                )

            elif direction == "received":
                queryset = queryset.filter(
                    to_account__in=accounts
                )

        from_date = filters.get("from_date")
        to_date = filters.get("to_date")

        if from_date:
            queryset = queryset.filter(
                created_at__date__gte=from_date
            )

        if to_date:
            queryset = queryset.filter(
                created_at__date__lte=to_date
            )

        return queryset.order_by("-created_at")


class TransactionDetailView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: TransactionSerializer,
            404: {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                    },
                },
            },
        },
        tags=["transactions"],
    )
    def get(self, request, pk):
        accounts = Account.objects.filter(
            user=request.user
        )

        transaction = (
            Transaction.objects
            .filter(pk=pk)
            .filter(
                Q(from_account__in=accounts)
                | Q(to_account__in=accounts)
            )
            .first()
        )

        if not transaction:
            return Response(
                {"detail": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TransactionSerializer(transaction)

        return Response(serializer.data)