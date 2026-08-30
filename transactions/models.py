from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Account


class TransactionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    REVERSED = "REVERSED", "Reversed"


class Transaction(models.Model):
    from_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
    )

    to_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="incoming_transactions",
    )

    status = models.CharField(
        max_length=10,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )

    amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction {self.pk} - {self.amount} {self.status}"