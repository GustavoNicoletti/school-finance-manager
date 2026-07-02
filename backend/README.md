# Backend

FastAPI backend for the School Finance Manager portfolio project.

## Features

- Authentication with JWT and `HttpOnly` cookies.
- User, role and permission management.
- Student and guardian CRUD.
- Receivables and payables CRUD.
- Batch tuition generation with duplicate protection.
- Financial dashboard, delinquency and cash-flow endpoints.
- Audit trail for business operations.
- XLSX/PDF/CSV exports for financial reports.

## Requirements

- Python 3.11+
- PostgreSQL 14+

## Local Setup

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs are available in local mode at:

```text
http://127.0.0.1:8000/api/docs
```

## Demo Seed

Optional synthetic data:

```bash
python -m app.seed_demo
```

The demo seed is only for local exploration and should not be used as production data.

## Main Endpoints

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/users`
- `GET/PUT /api/role-permissions`
- `GET/POST/PUT/DELETE /api/students`
- `GET/POST/PUT/DELETE /api/guardians`
- `GET/POST/PUT/DELETE /api/finance/receivables`
- `GET/POST/PUT/DELETE /api/finance/payables`
- `POST /api/finance/receivables/generate-batch`
- `GET /api/finance/delinquency`
- `GET /api/finance/cash-flow`
- `GET /api/reports/*`
- `GET /api/dashboard`
- `GET /api/audit`
- `GET /health`
- `GET /health/db`

## Tests

Use a dedicated PostgreSQL test database. The app refuses to run the test suite against a database name that does not look like a test database.

```bash
python -m pytest
```

## Security Notes

This public repository contains only placeholders and demo credentials. For any real deployment, replace all values in `.env`, use a dedicated PostgreSQL user, configure explicit CORS origins and keep API docs disabled outside local mode.
