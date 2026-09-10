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
#user means that the account is linked to a specific user in the system. 
# The ForeignKey establishes a many-to-one relationship, meaning that each account belongs to one user, but a user can have multiple accounts. 
# The on_delete=models.CASCADE argument specifies that if the user is deleted, all associated accounts will also be deleted. 
# The related_name="accounts" allows you to access a user's accounts using user.accounts.
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
        #This tells Django to create a database index on the combination of the user and status fields.
        #Think of an index like the index at the back of a textbook.
        #without an index, if you wanted to find all accounts for a specific user with a specific status, 
        # the database would have to look through every account record one by one until it found the right ones.
        #With an index, the database can quickly locate the relevant records,
        # much like how you can quickly find a topic in a textbook by looking it up in the index.
        #This can significantly speed up queries that filter on these fields, especially in a large database.
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.currency}"