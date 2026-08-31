from rest_framework.test import APIClient
from decimal import Decimal
import threading

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from accounts.models import Account
from ledger.models import LedgerEntry, LedgerEntryType
from ledger.services import get_account_balance
from transactions.models import Transaction, TransactionStatus
from transactions.services import transfer_money
from users.models import User


class TransferMoneyTests(TestCase):

    def setUp(self):
        self.sender_user = User.objects.create_user(
            email="sender@example.com",
            name="Sender",
            password="testpassword123",
        )

        self.receiver_user = User.objects.create_user(
            email="receiver@example.com",
            name="Receiver",
            password="testpassword123",
        )

        self.sender = Account.objects.create(
            user=self.sender_user,
            currency="KES",
            status="active",
        )

        self.receiver = Account.objects.create(
            user=self.receiver_user,
            currency="KES",
            status="active",
        )

        self.initial_balance = Decimal("5000.00")

        # Create a transaction representing the initial funding.
        funding_transaction = Transaction.objects.create(
            from_account=self.sender,
            to_account=self.receiver,
            amount=self.initial_balance,
            idempotency_key="initial-funding-001",
            status=TransactionStatus.COMPLETED,
        )

        # Give sender the initial balance through the ledger.
        LedgerEntry.objects.create(
            account=self.sender,
            transaction=funding_transaction,
            amount=self.initial_balance,
            entry_type=LedgerEntryType.CREDIT,
        )

    def test_successful_transfer(self):
        transaction = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="test-transfer-001",
        )

        self.assertEqual(
            transaction.status,
            TransactionStatus.COMPLETED,
        )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("4000.00"),
        )

        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transaction.objects.filter(
                idempotency_key="test-transfer-001"
            ).count(),
            1,
        )

        self.assertEqual(
            LedgerEntry.objects.filter(
                transaction=transaction
            ).count(),
            2,
        )

    def test_insufficient_balance(self):
        with self.assertRaisesMessage(
            ValueError,
            "Insufficient balance",
        ):
            transfer_money(
                from_account_id=self.sender.pk,
                to_account_id=self.receiver.pk,
                amount=Decimal("6000.00"),
                idempotency_key="insufficient-balance-test-001",
            )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("5000.00"),
        )

        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("0.00"),
        )

        self.assertFalse(
            Transaction.objects.filter(
                idempotency_key="insufficient-balance-test-001"
            ).exists()
        )

    def test_idempotency(self):
        first_transaction = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="idempotency-test-001",
        )

        second_transaction = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="idempotency-test-001",
        )

        self.assertEqual(
            first_transaction.pk,
            second_transaction.pk,
        )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("4000.00"),
        )

        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("1000.00"),
        )

        self.assertEqual(
            Transaction.objects.filter(
                idempotency_key="idempotency-test-001"
            ).count(),
            1,
        )

    def test_inactive_sender(self):
        self.sender.status = "inactive"
        self.sender.save(update_fields=["status"])

        with self.assertRaisesMessage(
            ValueError,
            "Sender account is not active",
        ):
            transfer_money(
                from_account_id=self.sender.pk,
                to_account_id=self.receiver.pk,
                amount=Decimal("1000.00"),
                idempotency_key="inactive-sender-test-001",
            )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("5000.00"),
        )

        self.assertFalse(
            Transaction.objects.filter(
                idempotency_key="inactive-sender-test-001"
            ).exists()
        )

    def test_inactive_receiver(self):
        self.receiver.status = "inactive"
        self.receiver.save(update_fields=["status"])

        with self.assertRaisesMessage(
            ValueError,
            "Receiver account is not active",
        ):
            transfer_money(
                from_account_id=self.sender.pk,
                to_account_id=self.receiver.pk,
                amount=Decimal("1000.00"),
                idempotency_key="inactive-receiver-test-001",
            )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("5000.00"),
        )

        self.assertFalse(
            Transaction.objects.filter(
                idempotency_key="inactive-receiver-test-001"
            ).exists()
        )

    def test_same_account_transfer(self):
        with self.assertRaisesMessage(
            ValueError,
            "Cannot transfer money to the same account",
        ):
            transfer_money(
                from_account_id=self.sender.pk,
                to_account_id=self.sender.pk,
                amount=Decimal("1000.00"),
                idempotency_key="same-account-test-001",
            )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("5000.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            1,
        )

        self.assertEqual(
            LedgerEntry.objects.count(),
            1,
        )

    def test_invalid_account(self):
        with self.assertRaisesMessage(
            ValueError,
            "Invalid from_account or to_account",
        ):
            transfer_money(
                from_account_id=99999,
                to_account_id=self.receiver.pk,
                amount=Decimal("1000.00"),
                idempotency_key="invalid-account-test-001",
            )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("5000.00"),
        )

        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("0.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            1,
        )

        self.assertEqual(
            LedgerEntry.objects.count(),
            1,
        )


class TransferMoneyConcurrencyTests(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        self.sender_user = User.objects.create_user(
            email="concurrent-sender@example.com",
            name="Concurrent Sender",
            password="testpassword123",
        )

        self.receiver_user = User.objects.create_user(
            email="concurrent-receiver@example.com",
            name="Concurrent Receiver",
            password="testpassword123",
        )

        self.sender = Account.objects.create(
            user=self.sender_user,
            currency="KES",
            status="active",
        )

        self.receiver = Account.objects.create(
            user=self.receiver_user,
            currency="KES",
            status="active",
        )

        initial_balance = Decimal("5000.00")

        # Create a transaction representing the initial funding.
        funding_transaction = Transaction.objects.create(
            from_account=self.sender,
            to_account=self.receiver,
            amount=initial_balance,
            idempotency_key="concurrency-initial-funding-001",
            status=TransactionStatus.COMPLETED,
        )

        # Give sender the initial balance through the ledger.
        LedgerEntry.objects.create(
            account=self.sender,
            transaction=funding_transaction,
            amount=initial_balance,
            entry_type=LedgerEntryType.CREDIT,
        )

    def test_concurrent_transfers_cannot_overspend(self):
        results = []
        errors = []

        def make_transfer(idempotency_key):
            close_old_connections()

            try:
                result = transfer_money(
                    from_account_id=self.sender.pk,
                    to_account_id=self.receiver.pk,
                    amount=Decimal("4000.00"),
                    idempotency_key=idempotency_key,
                )

                results.append(result)

            except Exception as error:
                errors.append(error)

            finally:
                close_old_connections()

        thread_one = threading.Thread(
            target=make_transfer,
            args=("concurrent-transfer-001",),
        )

        thread_two = threading.Thread(
            target=make_transfer,
            args=("concurrent-transfer-002",),
        )

        thread_one.start()
        thread_two.start()

        thread_one.join()
        thread_two.join()

        # Exactly one transfer should succeed.
        self.assertEqual(
            len(results),
            1,
        )

        # Exactly one transfer should fail.
        self.assertEqual(
            len(errors),
            1,
        )

        # Sender must have exactly KES 1,000 remaining.
        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("1000.00"),
        )

        # Receiver must have received exactly KES 4,000.
        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("4000.00"),
        )

        # Exactly one of the concurrent transfers completed.
        self.assertEqual(
            Transaction.objects.filter(
                status=TransactionStatus.COMPLETED,
                idempotency_key__startswith="concurrent-transfer-",
            ).count(),
            1,
        )

        # The successful transfer must have two ledger entries:
        # one debit and one credit.
        self.assertEqual(
            LedgerEntry.objects.filter(
                transaction=results[0],
            ).count(),
            2,
        )

class TransactionAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.sender_user = User.objects.create_user(
            email="api-sender@example.com",
            name="API Sender",
            password="testpassword123",
        )

        self.receiver_user = User.objects.create_user(
            email="api-receiver@example.com",
            name="API Receiver",
            password="testpassword123",
        )

        self.other_user = User.objects.create_user(
            email="api-other@example.com",
            name="Other User",
            password="testpassword123",
        )

        self.sender = Account.objects.create(
            user=self.sender_user,
            currency="KES",
            status="active",
        )

        self.receiver = Account.objects.create(
            user=self.receiver_user,
            currency="KES",
            status="active",
        )

        self.other_account = Account.objects.create(
            user=self.other_user,
            currency="KES",
            status="active",
        )

        self.initial_balance = Decimal("5000.00")

        funding_transaction = Transaction.objects.create(
            from_account=self.sender,
            to_account=self.receiver,
            amount=self.initial_balance,
            idempotency_key="api-initial-funding-001",
            status=TransactionStatus.COMPLETED,
        )

        LedgerEntry.objects.create(
            account=self.sender,
            transaction=funding_transaction,
            amount=self.initial_balance,
            entry_type=LedgerEntryType.CREDIT,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_authenticated_transfer(self):
        self.authenticate(self.sender_user)

        response = self.client.post(
            "/api/transactions/transfer/",
            {
                "to_account_id": self.receiver.pk,
                "amount": "1000.00",
                "idempotency_key": "api-transfer-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["amount"],
            "1000.00",
        )

        self.assertEqual(
            response.data["status"],
            "COMPLETED",
        )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("4000.00"),
        )

        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("1000.00"),
        )

    def test_unauthenticated_transfer(self):
        response = self.client.post(
            "/api/transactions/transfer/",
            {
                "to_account_id": self.receiver.pk,
                "amount": "1000.00",
                "idempotency_key": "api-unauthenticated-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_insufficient_balance(self):
        self.authenticate(self.sender_user)

        response = self.client.post(
            "/api/transactions/transfer/",
            {
                "to_account_id": self.receiver.pk,
                "amount": "6000.00",
                "idempotency_key": "api-insufficient-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "Insufficient balance",
            response.data["detail"],
        )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("5000.00"),
        )

    def test_invalid_receiver(self):
        self.authenticate(self.sender_user)

        response = self.client.post(
            "/api/transactions/transfer/",
            {
                "to_account_id": 99999,
                "amount": "1000.00",
                "idempotency_key": "api-invalid-receiver-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "to_account_id",
            response.data,
        )

    def test_same_account_transfer(self):
        self.authenticate(self.sender_user)

        response = self.client.post(
            "/api/transactions/transfer/",
            {
                "to_account_id": self.sender.pk,
                "amount": "1000.00",
                "idempotency_key": "api-same-account-001",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "Cannot transfer money to the same account",
        )

    def test_transaction_list_only_returns_user_transactions(self):
        self.authenticate(self.sender_user)

        transfer = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="api-list-001",
        )

        response = self.client.get(
            "/api/transactions/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        returned_ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertIn(
            transfer.pk,
            returned_ids,
        )

        # The sender should not see transactions belonging
        # exclusively to another user.
        other_transaction = Transaction.objects.create(
            from_account=self.other_account,
            to_account=self.receiver,
            amount=Decimal("500.00"),
            idempotency_key="api-other-transaction-001",
            status=TransactionStatus.COMPLETED,
        )

        response = self.client.get(
            "/api/transactions/"
        )

        returned_ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertNotIn(
            other_transaction.pk,
            returned_ids,
        )

    def test_transaction_detail(self):
        self.authenticate(self.sender_user)

        transfer = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="api-detail-001",
        )

        response = self.client.get(
            f"/api/transactions/{transfer.pk}/"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["id"],
            transfer.pk,
        )

        self.assertEqual(
            response.data["amount"],
            "1000.00",
        )

    def test_user_cannot_access_another_users_transaction(self):
        self.authenticate(self.sender_user)

        other_transaction = Transaction.objects.create(
            from_account=self.other_account,
            to_account=self.receiver,
            amount=Decimal("500.00"),
            idempotency_key="api-private-transaction-001",
            status=TransactionStatus.COMPLETED,
        )

        response = self.client.get(
            f"/api/transactions/{other_transaction.pk}/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            response.data["detail"],
            "Transaction not found.",
        )
        
    def test_transfer_idempotency(self):
        self.authenticate(self.sender_user)

        payload = {
            "to_account_id": self.receiver.pk,
            "amount": "1000.00",
            "idempotency_key": "api-idempotency-001",
        }

        # First request
        first_response = self.client.post(
            "/api/transactions/transfer/",
            payload,
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)

        # Second request with the exact same idempotency key
        second_response = self.client.post(
            "/api/transactions/transfer/",
            payload,
            format="json",
        )

        self.assertEqual(second_response.status_code, 200)

        # Both requests should refer to the same transaction.
        self.assertEqual(
            first_response.data["id"],
            second_response.data["id"],
        )

        # The transfer must only happen once.
        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("4000.00"),
        )

        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("1000.00"),
        )

        # Only one transaction should have been created.
        self.assertEqual(
            Transaction.objects.filter(
                idempotency_key="api-idempotency-001"
            ).count(),
            1,
        )
        
    def test_transaction_filter_by_status(self):
        self.authenticate(self.sender_user)

        transfer = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="filter-status-001",
        )

        response = self.client.get(
            "/api/transactions/?status=COMPLETED"
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertIn(transfer.pk, returned_ids)


    def test_transaction_filter_by_direction_sent(self):
        self.authenticate(self.sender_user)

        transfer = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="filter-sent-001",
        )

        response = self.client.get(
            "/api/transactions/?direction=sent"
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertIn(transfer.pk, returned_ids)


    def test_transaction_filter_by_direction_received(self):
        self.authenticate(self.receiver_user)

        transfer = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="filter-received-001",
        )

        response = self.client.get(
            "/api/transactions/?direction=received"
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertIn(transfer.pk, returned_ids)


    def test_transaction_filter_by_date_range(self):
        self.authenticate(self.sender_user)

        transfer = transfer_money(
            from_account_id=self.sender.pk,
            to_account_id=self.receiver.pk,
            amount=Decimal("1000.00"),
            idempotency_key="filter-date-001",
        )

        transaction_date = transfer.created_at.date()

        response = self.client.get(
            "/api/transactions/",
            {
                "from_date": transaction_date,
                "to_date": transaction_date,
            },
        )

        self.assertEqual(response.status_code, 200)

        returned_ids = [
            item["id"]
            for item in response.data["results"]
        ]

        self.assertIn(transfer.pk, returned_ids)
        
    def test_transaction_filter_rejects_invalid_date_range(self):
        self.authenticate(self.sender_user)

        response = self.client.get(
            "/api/transactions/"
            "?from_date=2026-08-31"
            "&to_date=2026-08-30"
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "from_date",
            response.data["non_field_errors"][0],
        )
    
    def test_unauthenticated_transaction_list(self):
        response = self.client.get(
            "/api/transactions/"
        )

        self.assertEqual(response.status_code, 401)


    def test_unauthenticated_transaction_detail(self):
        response = self.client.get(
            "/api/transactions/99999/"
        )

        self.assertEqual(response.status_code, 401)


    def test_transaction_detail_not_found(self):
        self.authenticate(self.sender_user)

        response = self.client.get(
            "/api/transactions/99999/"
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            response.data["detail"],
            "Transaction not found.",
        )


    def test_invalid_date_format(self):
        self.authenticate(self.sender_user)

        response = self.client.get(
            "/api/transactions/",
            {
                "from_date": "not-a-date",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "from_date",
            response.data,
        )


    def test_from_date_cannot_be_later_than_to_date(self):
        self.authenticate(self.sender_user)

        response = self.client.get(
            "/api/transactions/",
            {
                "from_date": "2026-08-31",
                "to_date": "2026-08-30",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "from_date cannot be later than to_date",
            response.data["non_field_errors"][0],
        )


    def test_idempotency_prevents_duplicate_api_transfer(self):
        self.authenticate(self.sender_user)

        payload = {
            "to_account_id": self.receiver.pk,
            "amount": "1000.00",
            "idempotency_key": "api-idempotency-001",
        }

        first_response = self.client.post(
            "/api/transactions/transfer/",
            payload,
            format="json",
        )

        second_response = self.client.post(
            "/api/transactions/transfer/",
            payload,
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

        self.assertEqual(
            first_response.data["id"],
            second_response.data["id"],
        )

        self.assertEqual(
            Transaction.objects.filter(
                idempotency_key="api-idempotency-001"
            ).count(),
            1,
        )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("4000.00"),
        )

        self.assertEqual(
            get_account_balance(self.receiver),
            Decimal("1000.00"),
        )
        
    def test_inactive_receiver_is_rejected(self):
        self.authenticate(self.sender_user)

        self.receiver.status = "inactive"
        self.receiver.save(update_fields=["status"])

        response = self.client.post(
            "/api/transactions/transfer/",
            {
                "to_account_id": self.receiver.pk,
                "amount": "1000.00",
                "idempotency_key": "api-inactive-receiver-001",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "to_account_id",
            response.data,
        )

        self.assertEqual(
            get_account_balance(self.sender),
            Decimal("5000.00"),
        )

        self.assertEqual(
            Transaction.objects.count(),
            1,
        )


    def test_invalid_status_filter_is_rejected(self):
        self.authenticate(self.sender_user)

        response = self.client.get(
            "/api/transactions/?status=INVALID",
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "status",
            response.data,
        )


    def test_invalid_direction_filter_is_rejected(self):
        self.authenticate(self.sender_user)

        response = self.client.get(
            "/api/transactions/?direction=INVALID",
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn(
            "direction",
            response.data,
        )