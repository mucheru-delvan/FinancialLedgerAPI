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
