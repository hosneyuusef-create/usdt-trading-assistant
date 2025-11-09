# Test Coverage Analysis

- **Version:** 1.0.0  
- **Owner:** Codex Autonomous Agent  
- **Last Reviewed:** 2025-11-08

## Overview

- **Backend unit / integration:** Vitest + Supertest + Knex test DB. Suites: `tests/user.test.ts`,
  `tests/rfq.test.ts`, `tests/settlement-flag.test.ts`. Approx. 85% statement coverage across
  `src/domain`.
- **Backend performance:** Vitest harness in `tests/performance/settlement-stress.test.ts`,
  exercising flag-off and flag-on batches in under 120 seconds.
- **Frontend component tests:** Vitest + Testing Library in `src/App.test.tsx`, covering
  validation, error surfacing, and submission flows.
- **Smoke / e2e-lite:** `scripts/manual-smoke.ts` and `scripts/check-approval-reason.ts` cover
  end-to-end approvals and REST validation outside of UI.
- **CI validation:** GitHub Actions workflow (lint + tests + docs + build + audits + docker
  health/rollback). Latest run:
  [19191541763](https://github.com/hosneyuusef-create/usdt-trading-assistant/actions/runs/19191541763/job/54866674041).

## Coverage Gaps & Actions

| Gap | Impact | Mitigation / Plan |
| --- | --- | --- |
| Frontend only has component tests (no E2E) | Medium | Add Playwright approve/reject smoke after backend auth endpoints ship (Phase 6+) |
| Wallet domain lacks dedicated unit tests beyond integration smoke | Medium | Add Vitest specs stubbing Knex to verify balance math + gauge resets |
| Telegram bot not exercised under CI | Low | Add mocked grammy handler tests (Phase 8) to enforce webhook secrets |
| `docs` linting ensures formatting but content verification manual | Low | Keep markdownlint gate + add release checklist rows in `REPORT.md` |

## Test Execution Checklist

- `npm run docs:lint`
- Backend suite:

  ```bash
  cd backend && npm run lint && npm test && npm run build \
    && npm audit --omit=dev --audit-level=high && npm audit --audit-level=high
  ```

- Frontend suite:

  ```bash
  cd frontend && npm run lint && npm test && npm run build \
    && npm audit --omit=dev --audit-level=high && npm audit --audit-level=high
  ```

- Docker deploy smoke:

  ```bash
  docker compose up --build -d
  curl <http://127.0.0.1:9090/health>
  docker compose down
  ```

  *(executed automatically in CI)*.

All commands above are captured in `REPORT.md` and enforced via GitHub Actions.
