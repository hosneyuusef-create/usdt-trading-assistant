# USDT Trading Assistant

Fastify + PostgreSQL stack for the USDT trading assistant described in `AGENTS.md`. The repo currently contains the
backend API (including the Telegram bot), the ops console frontend, documentation, and CI/CD assets.

## Repository Layout

- `backend/` - Fastify API, domain logic, migrations, Telegram bot integration
- `frontend/` - Vite/React ops console used by dual-control approvers
- `docs/` - Living runbooks (`dual_control.md`, `settlement_flag.md`, etc.)
- `REPORT.md` - Execution log (phase-by-phase evidence, commands, and risks)
- `.github/workflows/ci.yml` - Full pipeline (lint -> tests -> docs -> build -> audit -> deploy/rollback)

## Developer Setup

### Prerequisites

- Node.js >= 18.19
- npm >= 10
- PostgreSQL >= 16
- Docker (required for the Compose-based deploy step)

### Backend bootstrap

```bash
cd backend
npm install
cp .env.example .env       # update DB_URL/TEST_DB_URL/JWT_SECRET/etc.
npm run migrate:dev
npm test
```

### Frontend bootstrap

```bash
cd frontend
npm install
npm run dev                # http://127.0.0.1:5173 (proxied to backend API)
```

## PostgreSQL Guidance

### Default URLs

- Dev: `postgres://postgres:postgres@127.0.0.1:55432/usdt_trading_dev`
- Test: `postgres://postgres:postgres@127.0.0.1:55432/usdt_trading_test`

Override via `.env` or environment variables (`DB_URL`, `TEST_DB_URL`) when running in CI or containers.

### Migrations & Backups

- Apply latest: `cd backend && npm run migrate:dev`
- Roll back last batch: `cd backend && npm run migrate:rollback`
- Test DB migrations execute automatically in `npm test`
- Backups: `pg_dump $DB_URL > backups/usdt_trading_$(date +%Y%m%d).sql`
- Restore: `psql $DB_URL < backup.sql`

## Manual Smoke (Phase 1 Evidence)

```bash
cd backend
npx tsx scripts/manual-smoke.ts
```

The script seeds approvers, creates a pending ops user, routes it through dual-control approval, and logs the resulting
row. Verify with:

```sql
SELECT email, status FROM users WHERE email = 'smoke-user@example.com';
```

## Dual-Control Updates (Phase 2)

- Approval payloads must include:
  - `reason` (>= 5 characters) explaining the change
  - `secondaryApproverId` (must differ from `approverId`)
- Backend rejects missing reason / duplicate approver with HTTP 400 (see `scripts/check-approval-reason.ts`).
- Ops console mirrors the same validation and surfaces Fastify/Zod errors inline.
- Runbook: `docs/dual_control.md` (workflow, payload examples, manual test checklist).

## AUTO_SETTLEMENT Feature Flag (Phase 3)

- `AUTO_SETTLEMENT_ENABLED` can be toggled via `.env`, the `feature_flags` table, or API writes (default `false`
  locally). Full runbook: `docs/settlement_flag.md`.
- Flag **OFF**
  - Settlement jobs are not queued; instead a record is written to `settlement_flagged_events`.
  - Metrics update: `auto_settlement_status=0`, `flagged_off_total`,
    `settlement_flagged_total{reason="AUTO_SETTLEMENT_DISABLED"}`.
  - Alert rule `auto_settlement_disabled` fires (debounced 60 s). Evidence: `npx tsx scripts/check-approval-reason.ts`
    and `psql ... SELECT * FROM settlement_flagged_events`.
- Flag **ON**
  - `acceptQuote` routes through `scheduleSettlementWorkItem`, inserting settlement + job entries asynchronously.
  - Metrics update: `auto_settlement_status=1`, `settlement_queue_size`.
- Tests / verification:
  - `npm test -- tests/settlement-flag.test.ts`
  - `npm test -- tests/performance/settlement-stress.test.ts` (flag-off/on batches complete <120 s)
  - `npx tsx scripts/manual-smoke.ts`

## Frontend Ops Console

- `npm run dev` - dual-control panel with validation, error surfacing, and manual refresh
- `npm test` - Testing Library coverage for validation + submission paths
- `VITE_API_BASE_URL` defaults to `http://127.0.0.1:9090/api`

## CI/CD & Deploy

### Pipeline (`.github/workflows/ci.yml`)

| Stage | Description |
| --- | --- |
| Lint | `npm run lint` (backend) + `npm run lint` (frontend) |
| Tests | `npm test` (backend) + `npm test` (frontend) |
| Docs Lint | `npm run docs:lint` (markdownlint across README + docs) |
| Build | `npm run build` (backend TypeScript) + `npm run build` (frontend Vite) |
| Security | `npm audit --omit=dev --audit-level=high` and `npm audit --audit-level=high` in both packages |
| Deploy | `docker compose up --build -d`, `/health` probe, automatic rollback on failure |

### Local dry-run commands

```bash
npm run docs:lint

cd backend
npm run lint
npm test
npm run build
npm audit --omit=dev --audit-level=high
npm audit --audit-level=high

cd ../frontend
npm run lint
npm test
npm run build
npm audit --omit=dev --audit-level=high
npm audit --audit-level=high
```

### Compose Deploy / Rollback

```bash
docker compose up --build -d
curl --fail --retry 5 --retry-delay 2 http://127.0.0.1:9090/health

# rollback on failure (abridged)
docker compose logs backend
docker compose down
exit 1

# when successful
docker compose down
```

Compose services:

- `postgres` - PostgreSQL 16 with health checks and seeded databases
- `backend` - Fastify API container (`npm run migrate:dev && node dist/server/index.js`)
- `frontend` - Nginx serving the Vite build (port 4173 mapped to container port 80)

The GitHub workflow mirrors these commands; if `/health` fails the job captures logs and rolls everything back.
