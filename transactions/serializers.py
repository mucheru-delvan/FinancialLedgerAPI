from decimal import Decimal

from rest_framework import serializers

from accounts.models import Account
from transactions.models import Transaction

class TransferSerializer(serializers.Serializer):
    to_account_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    idempotency_key = serializers.CharField(max_length=255)

    def validate_to_account_id(self, value):
        if not Account.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "Receiver account does not exist."
            )

        return value
from datetime import date

class TransactionFilterSerializer(serializers.Serializer):
    status = serializers.CharField(required=False)
    direction = serializers.CharField(required=False)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")

        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError(
                "from_date cannot be later than to_date."
            )

        return attrs

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "from_account",
            "to_account",
            "amount",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "from_account",
            "to_account",
            "status",
            "created_at",
            "updated_at",
        ]
