# School Finance Manager

Full-stack school management system focused on financial control, student records and operational dashboards.

The project was designed around a common school administration problem: keeping students, guardians, monthly charges, expenses, delinquency and cash flow organized in one place.

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

Use the `.env.example` files as templates only. Replace every credential before using the project outside a local environment.

This repository keeps infrastructure configuration generic. Production domains, cloud resources, database hosts and secrets are not part of the codebase.

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

The repository uses synthetic data and placeholder configuration. It focuses on the application structure, financial rules, access control and user flows without exposing any real production environment.
