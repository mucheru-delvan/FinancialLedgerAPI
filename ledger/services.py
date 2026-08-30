from decimal import Decimal

from django.db.models import Sum

from ledger.models import LedgerEntry, LedgerEntryType


def get_account_balance(account):
    total_credit = (
        LedgerEntry.objects
        .filter(
            account=account,
            entry_type=LedgerEntryType.CREDIT,
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    total_debit = (
        LedgerEntry.objects
        .filter(
            account=account,
            entry_type=LedgerEntryType.DEBIT,
        )
        .aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    return total_credit - total_debit