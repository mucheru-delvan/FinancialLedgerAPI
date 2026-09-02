from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from accounts.models import Account
from accounts.serializers import AccountSerializer


class MyAccountView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: AccountSerializer,
            404: {
                "type": "object",
                "properties": {
                    "detail": {
                        "type": "string",
                    },
                },
            },
        },
        tags=["accounts"],
    )
    def get(self, request):
        account = (
            Account.objects
            .filter(
                user=request.user,
                status="active",
            )
            .first()
        )

        if not account:
            return Response(
                {"detail": "Active account not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AccountSerializer(account)

        return Response(serializer.data)