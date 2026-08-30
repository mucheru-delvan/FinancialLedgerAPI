from django.db import models


# Create your models here.
from django.core.validators import MinValueValidator
from accounts.models import Account
from transactions.models import Transaction

class LedgerEntryType(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    DEBIT = "DEBIT", "Debit"
    #This determines whether the entry is a credit or debit to the account.
    # A credit increases the account balance, while a debit decreases it.
    
class LedgerEntry(models.Model):
    account = models.ForeignKey(
    Account,
    on_delete=models.PROTECT,
    related_name="ledger_entries",
    )
    
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    
    entry_type = models.CharField(
    max_length=6,
    choices=LedgerEntryType.choices,
    )
