# FinancialLedgerAPI

A RESTful financial ledger API built with Django REST Framework and PostgreSQL for managing user accounts, financial transactions, and double-entry ledger records.

The project focuses on secure authentication, reliable money transfers, transaction integrity, idempotency, concurrency handling, and production deployment.

## Features

* User registration and authentication
* JWT-based authentication
* Access and refresh tokens
* Refresh token rotation and blacklisting
* User account management
* Financial account balances
* Money transfers between accounts
* Double-entry ledger records
* Transaction status tracking
* Idempotent transfers using idempotency keys
* Database transaction atomicity
* Row-level locking for concurrent transfers
* Currency validation
* Account status validation
* Transaction history
* Transaction filtering
* Pagination
* API throttling
* OpenAPI schema and Swagger documentation
* Automated tests
* Docker containerization
* PostgreSQL database
* Production deployment with Render and Neon

## Tech Stack

| Technology            | Purpose                                      |
| --------------------- | -------------------------------------------- |
| Python                | Backend programming language                 |
| Django                | Web framework                                |
| Django REST Framework | REST API development                         |
| PostgreSQL            | Relational database                          |
| SimpleJWT             | JWT authentication                           |
| drf-spectacular       | OpenAPI/Swagger documentation                |
| Docker                | Containerization                             |
| Gunicorn              | Production WSGI server                       |
| Nginx                 | Reverse proxy for local container setup      |
| Render                | Production application hosting               |
| Neon                  | Production PostgreSQL database               |
| uv                    | Python dependency and environment management |
| Git/GitHub            | Version control                              |

## Architecture

```text
Client
   │
   ▼
REST API
   │
   ▼
Django REST Framework
   │
   ├── Authentication / Permissions
   │
   ├── Serializers
   │
   ├── Views / ViewSets
   │
   ▼
Service Layer
   │
   ├── Transfer validation
   ├── Idempotency
   ├── Atomic transactions
   └── Concurrency control
   │
   ▼
PostgreSQL
   │
   ├── Accounts
   ├── Transactions
   └── Ledger Entries
```

### Production

```text
Internet
   │
   ▼
Render
   │
   ▼
Django + Gunicorn
   │
   ▼
Neon PostgreSQL
```

## Authentication

The API uses JWT authentication.

Users obtain access and refresh tokens through the authentication endpoints.

Access tokens are short-lived, while refresh tokens can be used to obtain new access tokens.

Refresh token rotation and blacklisting are enabled to prevent reuse of rotated refresh tokens.

Protected endpoints require:

```http
Authorization: Bearer <access_token>
```

## API Endpoints

### Authentication

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/token/refresh/
```

### Accounts

```text
GET /api/accounts/
GET /api/accounts/{id}/
```

### Transactions

```text
GET  /api/transactions/
GET  /api/transactions/{id}/
POST /api/transactions/transfer/
```

### Documentation

```text
GET /api/schema/
GET /api/docs/
```

## Money Transfer

Transfers are handled inside a database transaction.

The transfer process validates:

1. The sender and receiver are different accounts.
2. Both accounts exist.
3. Both accounts are active.
4. Both accounts use the same currency.
5. The idempotency key has not been used for a different transaction.
6. The sender has sufficient funds.

The accounts are locked using database row-level locking before the balance is checked.

This prevents concurrent transfers from spending the same balance.

Conceptually:

```text
Request
   │
   ▼
Validate transfer
   │
   ▼
Lock accounts
   │
   ▼
Check idempotency
   │
   ▼
Check balance
   │
   ▼
Create transaction
   │
   ▼
Create debit ledger entry
   │
   ▼
Create credit ledger entry
   │
   ▼
Mark transaction COMPLETED
```

If any operation fails, the database transaction is rolled back.

## Idempotency

Transfers require an `idempotency_key`.

This prevents accidental duplicate processing when the same request is submitted more than once.

For example:

```json
{
  "from_account_id": 1,
  "to_account_id": 2,
  "amount": "100.00",
  "idempotency_key": "transfer-001"
}
```

If the same request is submitted again with the same key, the existing transaction can be returned instead of creating another transfer.

If the same key is reused with different transaction details, the request is rejected.

## Ledger

The system records transfers using ledger entries.

A successful transfer creates:

```text
Sender Account
    │
    └── DEBIT 100.00

Receiver Account
    │
    └── CREDIT 100.00
```

The ledger provides a transaction history from which account balances can be calculated.

## Transaction Integrity

The transfer service uses Django's database transaction management:

```python
with transaction.atomic():
    ...
```

This ensures that related database operations succeed or fail together.

For example, if the debit entry succeeds but the credit entry fails, the entire transfer is rolled back.

## Concurrency Control

The transfer service uses:

```python
select_for_update()
```

to lock the accounts involved in a transfer.

Accounts are locked in a consistent order to reduce the risk of deadlocks.

This is important when multiple requests attempt to transfer money from the same account at the same time.

## Validation

The API validates:

* Positive transaction amounts
* Sender and receiver accounts
* Account status
* Currency compatibility
* Sufficient balance
* Idempotency keys
* User authorization

Example insufficient-balance response:

```json
{
  "detail": "Insufficient balance. Current balance is 0.00. Requested amount is 100.00."
}
```

## Pagination and Filtering

Transaction history supports pagination and filtering.

Example:

```text
GET /api/transactions/
```

Response:

```json
{
  "count": 10,
  "next": "...",
  "previous": null,
  "results": []
}
```

## API Throttling

The API uses DRF throttling to limit request rates.

Configured limits include:

```text
Anonymous users: 20 requests/minute
Authenticated users: 60 requests/minute
```

This provides basic protection against excessive API requests.

## Testing

The project includes automated tests covering areas such as:

* Successful transfers
* Insufficient funds
* Same-account transfers
* Invalid accounts
* Inactive accounts
* Currency mismatch
* Transaction rollback
* Idempotency
* Concurrent transfers
* Authorization
* Transaction filtering
* Transaction status filtering
* Pagination

The test suite has previously passed with:

```text
Ran 33 tests

OK
```

## Environment Variables

Sensitive configuration is stored in environment variables rather than committed to Git.

Example:

```env
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=your-postgresql-connection-string
SECURE_SSL_REDIRECT=True
```

The `.env` file is excluded from version control.

## Running Locally

Clone the repository:

```bash
git clone https://github.com/mucheru-delvan/FinancialLedgerAPI.git
cd FinancialLedgerAPI
```

Create and activate the virtual environment:

```bash
uv sync
source .venv/bin/activate
```

Run migrations:

```bash
uv run python manage.py migrate
```

Start the development server:

```bash
uv run python manage.py runserver
```

The API will be available at:

```text
http://127.0.0.1:8000/
```

Swagger documentation:

```text
http://127.0.0.1:8000/api/docs/
```

## Docker

The project includes Docker support for running the application in containers.

Build the image:

```bash
docker build -t financial-ledger-api .
```

Run the container:

```bash
docker run --rm \
  -p 8000:8000 \
  -e PORT=8000 \
  --env-file .env \
  financial-ledger-api
```

The project also includes Docker Compose for running Django, PostgreSQL, and Nginx together.

```bash
docker compose up --build
```

## Production Deployment

The API is deployed using:

* Render for the Django application
* Neon for PostgreSQL

Production architecture:

```text
Client
  │
  ▼
Render
  │
  ▼
Docker
  │
  ▼
Gunicorn
  │
  ▼
Django REST Framework
  │
  ▼
Neon PostgreSQL
```

Production API:

```text
https://financialledgerapi.onrender.com
```

Swagger:

```text
https://financialledgerapi.onrender.com/api/docs/
```

## Security

Security measures implemented include:

* JWT authentication
* Short-lived access tokens
* Refresh token rotation
* Refresh token blacklisting
* Password hashing through Django
* Authenticated API permissions
* Environment-based secrets
* HTTPS in production
* API throttling
* Database transactions
* Row-level locking
* Idempotent transaction processing
* Input validation

## Project Goals

This project was built to demonstrate practical backend engineering concepts relevant to financial systems, including:

* REST API design
* Authentication and authorization
* Relational database design
* Transaction processing
* ACID transactions
* Concurrency control
* Idempotency
* Testing
* Containerization
* Production deployment

