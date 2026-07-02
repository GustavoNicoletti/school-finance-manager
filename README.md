# School Finance Manager

Portfolio project for a school management system focused on financial control, student records and operational dashboards.

This repository is a sanitized public version. It does not include real school data, production credentials, infrastructure endpoints, private keys, database dumps or deployment secrets.

## Highlights

- JWT authentication with `HttpOnly` session cookies.
- Configurable role and permission matrix.
- Student and guardian management.
- Receivables, payables, delinquency and cash-flow control.
- Batch generation of monthly tuition charges with duplicate protection.
- Financial dashboard with month comparison.
- Audit trail for relevant operations.
- XLSX/PDF report exports with filters.
- Backend and frontend test suites for critical flows.

## Tech Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL.
- Frontend: React, TypeScript, Vite, Material UI, React Router, Axios.
- Quality: Pytest, Playwright smoke tests, GitHub Actions, dependency and secret scanning.

## Project Structure

```text
backend/
  app/
    core/
    models/
    routers/
    schemas/
    services/
  alembic/
  tests/

frontend/
  src/
    api/
    auth/
    components/
    layouts/
    pages/
    utils/
  tests/
```

## Local Setup

Backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Expected local URLs:

- Frontend: `http://127.0.0.1:5173`
- API health: `http://127.0.0.1:8000/health`
- API docs in local mode: `http://127.0.0.1:8000/api/docs`

## Environment

Use the `.env.example` files as templates only. Replace every credential before using the project outside a local demo environment.

This public version intentionally keeps infrastructure generic. Production domains, cloud resources, database hosts and secrets are not part of this repository.

## Demo Data

The backend includes an optional demo seed:

```bash
python -m app.seed_demo
```

The demo data is synthetic and should be used only for local exploration.

## Tests

Backend:

```bash
cd backend
python -m pytest
```

Frontend:

```bash
cd frontend
npm run build
npm run test:smoke:e2e
```

## Notes

This project was built as a practical full-stack case study for school financial management. The public repository focuses on architecture, code organization, business rules and UI flows, not on exposing any real production environment.
