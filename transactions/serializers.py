from decimal import Decimal

from rest_framework import serializers

from accounts.models import Account, AccountStatus
from transactions.models import Transaction, TransactionStatus


class TransferSerializer(serializers.Serializer):
    from_account_id = serializers.IntegerField()
    to_account_id = serializers.IntegerField()

    amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    idempotency_key = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )

    def validate_to_account_id(self, value):
        """
        Validate that the receiver account exists and is active.
        """
        try:
            account = Account.objects.get(pk=value)
        except Account.DoesNotExist:
            raise serializers.ValidationError(
                "Receiver account does not exist."
            )

        if account.status != AccountStatus.ACTIVE.value:
            raise serializers.ValidationError(
                "Receiver account is not active."
            )

        return value


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


class TransactionFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            TransactionStatus.PENDING.value,
            TransactionStatus.COMPLETED.value,
            TransactionStatus.FAILED.value,
            TransactionStatus.REVERSED.value,
        ],
        required=False,
    )

    direction = serializers.ChoiceField(
        choices=["sent", "received"],
        required=False,
    )

    from_date = serializers.DateField(
        required=False,
    )

    to_date = serializers.DateField(
        required=False,
    )

    def validate(self, attrs):
        """
        Validate that the date range is in chronological order.
        """
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")

        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError(
                "from_date cannot be later than to_date."
            )

        return attrs