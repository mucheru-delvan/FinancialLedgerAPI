from decimal import Decimal

from django.db import transaction

from accounts.models import Account, AccountStatus
from ledger.models import LedgerEntry, LedgerEntryType
from ledger.services import get_account_balance
from transactions.models import Transaction, TransactionStatus


def transfer_money(
    *,
    from_account_id,
    to_account_id,
    amount,
    idempotency_key,
):
    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValueError("Transaction amount must be greater than zero")

    if from_account_id == to_account_id:
        raise ValueError("Cannot transfer money to the same account")

    with transaction.atomic():

        # Lock both accounts in a consistent order.
        # This reduces the risk of deadlocks when transfers
        # happen simultaneously in opposite directions.
        accounts = (
            Account.objects
            .select_for_update()
            .filter(pk__in=[from_account_id, to_account_id])
            .order_by("pk")
        )

        accounts_by_id = {
            account.pk: account
            for account in accounts
        }

        from_account = accounts_by_id.get(from_account_id)
        to_account = accounts_by_id.get(to_account_id)

        if not from_account or not to_account:
            raise ValueError("Invalid from_account or to_account")

        if from_account.status != AccountStatus.ACTIVE.value:
            raise ValueError("Sender account is not active")

        if to_account.status != AccountStatus.ACTIVE.value:
            raise ValueError("Receiver account is not active")

        if from_account.currency != to_account.currency:
            raise ValueError(
                "Currency mismatch between sender and receiver accounts"
            )
                # Idempotency check.
        existing_transaction = (
            Transaction.objects
            .filter(idempotency_key=idempotency_key)
            .first()
        )

        if existing_transaction:
            if (
                existing_transaction.from_account_id != from_account_id
                or existing_transaction.to_account_id != to_account_id
                or existing_transaction.amount != amount
            ):
                raise ValueError(
                    "Idempotency key has already been used "
                    "for a different transaction."
                )

            return existing_transaction

            # Calculate balance while the account is locked.
        balance = get_account_balance(from_account)

        if balance < amount:
            raise ValueError(
                f"Insufficient balance. "
                f"Current balance is {balance}. "
                f"Requested amount is {amount}."
            )

        # Create transaction.
        new_transaction = Transaction.objects.create(
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            idempotency_key=idempotency_key,
            status=TransactionStatus.PENDING,
        )

        # Debit sender.
        LedgerEntry.objects.create(
            account=from_account,
            transaction=new_transaction,
            amount=amount,
            entry_type=LedgerEntryType.DEBIT,
        )

        # Credit receiver.
        LedgerEntry.objects.create(
            account=to_account,
            transaction=new_transaction,
            amount=amount,
            entry_type=LedgerEntryType.CREDIT,
        )

        # Everything succeeded.
        new_transaction.status = TransactionStatus.COMPLETED
        new_transaction.save(update_fields=["status"])

        return new_transaction