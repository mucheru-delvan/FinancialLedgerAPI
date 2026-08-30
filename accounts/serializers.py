from rest_framework import serializers

from accounts.models import Account
from ledger.services import get_account_balance


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "currency",
            "status",
            "balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_balance(self, account):
        balance = get_account_balance(account)
        return f"{balance:.2f}"