# Requirements Traceability Matrix

- **Version:** 1.0.0  
- **Owner:** Codex Autonomous Agent  
- **Last Reviewed:** 2025-11-08

| Req ID | Requirement | Implementation References | Validation / Evidence |
| --- | --- | --- | --- |
| R1 | Backend must run on PostgreSQL with vetted schema/migrations (Phase 1) | `backend/migrations/0001_initial_schema.cjs`, `backend/src/database`, README “PostgreSQL Guidance” | `npm run migrate:dev`, `npm test`, smoke script output logged in `REPORT.md` |
| R2 | Dual-control approvals demand reason + secondary approver (Phase 2) | `backend/migrations/0002_dual_control_secondary.cjs`, `backend/src/domain/dual-control.ts`, `frontend/src/App.tsx`, `docs/dual_control.md` | `npm test -- tests/user.test.ts`, `frontend npm test`, manual POST check via `scripts/check-approval-reason.ts` |
| R3 | AUTO_SETTLEMENT flag controls settlement queue & metrics (Phase 3) | `backend/migrations/0003_auto_settlement_flag.cjs`, `backend/src/domain/settlement.ts`, `docs/settlement_flag.md` | `npm test -- tests/settlement-flag.test.ts`, `npm test -- tests/performance/settlement-stress.test.ts`, Prometheus counters verified during tests |
| R4 | Observability: `/metrics` + alerting + audit logs | `backend/src/domain/metrics.ts`, `backend/src/domain/alerting.ts`, `backend/src/utils/audit.ts` | `curl /metrics` (documented), unit tests touching metrics & alert emission, audit rows confirmed in smoke script |
| R5 | Telegram bot integration for ops notifications | `backend/src/telegram/bot.ts`, Fastify hooks | Bot startup gated via env; smoke test ensures handler registration (logged in `REPORT.md`) |
| R6 | Ops console reacting to backend errors & validations | `frontend/src/App.tsx`, `frontend/src/App.test.tsx` | `npm run lint && npm test` in `frontend`, manual run instructions in README |
| R7 | CI/CD pipeline with lint → tests → docs → build → audits → docker health/rollback | `.github/workflows/ci.yml`, `docker-compose.yml`, README CI section | GitHub Actions Run [19191541763](https://github.com/hosneyuusef-create/usdt-trading-assistant/actions/runs/19191541763/job/54866674041) |
| R8 | Documentation pack (README + RTM + personas + risk + coverage) kept in sync | `README.md`, this file, `docs/personas.md`, `docs/risk_register.md`, `docs/TEST_COVERAGE_ANALYSIS.md` | `npm run docs:lint`, peer review checklist in `REPORT.md` |
| R9 | Security posture via npm audits (fail on High/Critical) | Workflow audit steps, `backend/package.json`, `frontend/package.json` | `npm audit --omit=dev --audit-level=high` (backend & frontend) in CI logs |
| R10 | Backup/restore & troubleshooting guidance | README “PostgreSQL Guidance” + “Troubleshooting” section | Markdownlint + manual review evidence in `REPORT.md` |
