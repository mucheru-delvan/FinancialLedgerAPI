from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Account
from accounts.serializers import AccountSerializer


class MyAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = Account.objects.get(
            user=request.user,
            status="active",
        )

        serializer = AccountSerializer(account)

        return Response(serializer.data)