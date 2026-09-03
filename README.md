# FinancialLedgerAPI

A RESTful API for managing financial accounts, transactions, and ledger records with secure authentication and reliable transaction processing.

## Overview

FinancialLedgerAPI is a backend financial ledger system built with Django REST Framework and PostgreSQL. It provides authenticated users with financial accounts and supports secure money transfers while maintaining consistent ledger records.

The system is designed around transactional integrity and account ownership, ensuring that transfers are processed atomically and users can only access financial resources they are authorized to use.

## Features

* User registration and JWT-based authentication
* Authenticated user profile access
* Financial account management
* Secure account-to-account transfers
* Transaction history and transaction details
* Transaction filtering by status, direction, and date
* Idempotent transfer processing to prevent duplicate transactions
* Database-level transaction locking for concurrent transfers
* Double-entry ledger records for transfers
* PostgreSQL database
* Interactive API documentation with Swagger
* Automated test suite for transaction workflows

## Tech Stack

* **Python**
* **Django**
* **Django REST Framework**
* **PostgreSQL**
* **JWT**
* **drf-spectacular**
* **Git & GitHub**
* **Swagger / OpenAPI**

## API Architecture

The API follows a layered approach:

```text
HTTP Request
     ↓
URL Routing
     ↓
Authentication / Permissions
     ↓
View
     ↓
Serializer / Validation
     ↓
Service Layer
     ↓
Database Transaction
     ↓
PostgreSQL
     ↓
Serializer
     ↓
JSON Response
```

The transfer workflow is handled through a dedicated service layer so that the business logic for transferring money remains separate from the HTTP/API layer.
## API Endpoints

### Authentication

| Method | Endpoint              | Description                               | Authentication |
| ------ | --------------------- | ----------------------------------------- | -------------- |
| `POST` | `/api/auth/register/` | Register a new user                       | No             |
| `POST` | `/api/auth/login/`    | Authenticate a user and obtain JWT tokens | No             |
| `GET`  | `/api/auth/me/`       | Retrieve the authenticated user's profile | JWT            |

### Accounts

| Method | Endpoint            | Description                                      | Authentication |
| ------ | ------------------- | ------------------------------------------------ | -------------- |
| `GET`  | `/api/accounts/me/` | Retrieve the authenticated user's active account | JWT            |

### Transactions

| Method | Endpoint                      | Description                                | Authentication |
| ------ | ----------------------------- | ------------------------------------------ | -------------- |
| `POST` | `/api/transactions/transfer/` | Transfer money between accounts            | JWT            |
| `GET`  | `/api/transactions/`          | Retrieve the user's transaction history    | JWT            |
| `GET`  | `/api/transactions/{id}/`     | Retrieve details of a specific transaction | JWT            |

## Transaction Processing

Transfers are processed through a dedicated service layer rather than placing the business logic directly inside the API view.

A transfer follows this process:

```text
Client
  ↓
Transfer API
  ↓
Validate request
  ↓
Verify account ownership
  ↓
Start database transaction
  ↓
Lock accounts
  ↓
Validate balances and account status
  ↓
Check idempotency key
  ↓
Create transaction
  ↓
Create debit ledger entry
  ↓
Create credit ledger entry
  ↓
Commit transaction
  ↓
Return response
```

The transfer operation uses database transactions and row-level locking to maintain consistency when multiple transfers are processed concurrently.

## Ledger Model

Each successful transfer produces two ledger entries:

```text
Sender Account
     ↓
DEBIT  - 100.00 KES

Receiver Account
     ↓
CREDIT + 100.00 KES
```

The account balance is derived from its ledger entries:

```text
Balance = Total Credits - Total Debits
```

This provides an auditable record of financial activity instead of relying only on a mutable balance value.

## Idempotency

Transfers require an idempotency key.

If a client retries the same request with the same key, the system prevents the transfer from being processed twice.

This protects against duplicate transactions caused by:

* Network retries
* Client retries
* Request timeouts
* Accidental duplicate submissions

## API Documentation

Interactive API documentation is available through Swagger:

```text
http://127.0.0.1:8000/api/docs/
```

The OpenAPI schema is available at:

```text
http://127.0.0.1:8000/api/schema/
```
## Security & Design

FinancialLedgerAPI uses several mechanisms to protect financial operations and maintain data consistency.

### JWT Authentication

The API uses JSON Web Tokens (JWT) for authentication. Protected endpoints require a valid access token, ensuring that only authenticated users can access financial resources.

### Authorization & Account Ownership

Authentication alone is not enough to access financial data. The API verifies that the authenticated user owns the account involved in an operation.

For example, a user cannot initiate a transfer using another user's account.

Transaction history is also restricted to transactions involving the authenticated user's accounts.

### Atomic Transactions

Money transfers are executed inside a database transaction using Django's `transaction.atomic()`.

This ensures that the transfer either completes fully or none of its changes are committed.

For example:

```text
Create Transaction
      +
Debit Sender
      +
Credit Receiver
      ↓
   COMMIT
```

If any operation fails, the entire transaction is rolled back.

### Row-Level Locking

The transfer service uses database row-level locking with `select_for_update()`.

Accounts involved in a transfer are locked while the transaction is being processed. This helps prevent race conditions when multiple transfers attempt to modify the same accounts concurrently.

### Idempotency

Each transfer requires an idempotency key.

If the same request is submitted again with the same key, the API prevents the transfer from being processed twice.

This is particularly useful when clients retry requests because of network failures or timeouts.

### Environment Variables

Sensitive configuration such as database credentials and Django's secret key is stored in environment variables through a `.env` file rather than being hard-coded in the source code.

The `.env` file should never be committed to version control.

### API-Level Protection

Protected endpoints use Django REST Framework's `IsAuthenticated` permission class.

The API also performs additional ownership checks at the application level before allowing financial operations.

These controls work together to ensure that authentication, authorization, and transaction processing are handled separately.
## Project Structure

```text
FinancialLedgerAPI/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── accounts/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── ...
│
├── transactions/
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── views.py
│   └── ...
│
├── users/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── ...
│
├── ledger/
│   ├── models.py
│   └── ...
│
├── manage.py
├── .env
├── .gitignore
└── README.md
```

### Application Responsibilities

| Component      | Responsibility                                                     |
| -------------- | ------------------------------------------------------------------ |
| `users`        | User registration, authentication, and user profile management     |
| `accounts`     | Financial account management and account ownership                 |
| `transactions` | Transfers, transaction history, filtering, and transaction details |
| `ledger`       | Ledger entries representing debits and credits                     |
| `config`       | Django project configuration, settings, and URL routing            |

### Service Layer

The transaction business logic is separated from the API views.

The `transactions/services.py` module is responsible for processing transfers, including:

* Validating account state
* Checking available balance
* Preventing transfers to the same account
* Applying database locks
* Handling idempotency
* Creating the transaction record
* Creating debit and credit ledger entries
* Executing the operation atomically

This separation keeps the API views focused on handling HTTP requests and responses while the service layer manages the core financial business logic.
## Testing

The project includes automated tests covering the core financial transaction workflows.

Run the test suite with:

```bash
python manage.py test
```

Run Django's system checks with:

```bash
python manage.py check
```

The tests cover important transaction scenarios such as:

* Successful transfers
* Insufficient account balance
* Invalid or inactive accounts
* Unauthorized account access
* Same-account transfers
* Duplicate transfers using idempotency keys
* Transaction rollback
* Concurrent transaction handling
* Ledger entry creation

The test suite helps verify that financial operations maintain data consistency and that invalid operations do not modify account balances or ledger records.

## Future Improvements

The following improvements could be added as the project evolves:

* Dockerize the application for consistent development and deployment environments
* Add CI/CD with GitHub Actions
* Deploy the API to a cloud platform
* Add API rate limiting
* Add refresh-token rotation and stronger JWT security controls
* Add comprehensive API integration tests
* Add structured application logging and monitoring
* Add database backups and recovery procedures
* Improve account support to allow multiple accounts per user
* Add pagination and performance optimizations for large transaction histories
* Add role-based access control for administrative operations
* Add support for additional transaction types
## License

This project is available for educational and portfolio purposes.


