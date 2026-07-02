# Frontend

React frontend for School Finance Manager.

## Features

- Login screen with API/database status.
- Authenticated dashboard layout with sidebar navigation.
- Permission-aware routes.
- Financial dashboard.
- Student and guardian management.
- Receivables and payables screens with filters and pagination.
- Delinquency, cash-flow and reports pages.
- User and role-permission management.

## Requirements

- Node.js 20+
- Backend running at `http://127.0.0.1:8000`

## Local Setup

```bash
npm install
copy .env.example .env
npm run dev
```

Local URL:

```text
http://127.0.0.1:5173
```

## Build

```bash
npm run build
```

## Smoke Test

```bash
npm run test:smoke:e2e
```

Optional environment variables:

- `E2E_API_URL`
- `E2E_ADMIN_EMAIL`
- `E2E_ADMIN_PASSWORD`

## Notes

The frontend uses `VITE_API_URL=/api` in local mode and the Vite proxy forwards requests to the backend. No production URL, bucket, distribution or private infrastructure configuration is included in this repository.
