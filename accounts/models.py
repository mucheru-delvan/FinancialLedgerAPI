from django.conf import settings
from django.db import models


class AccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    FROZEN = "frozen", "Frozen"
    CLOSED = "closed", "Closed"


class Account(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts",
    )

    status = models.CharField(
        max_length=10,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )

    currency = models.CharField(
        max_length=3,
        default="KES",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.currency}"