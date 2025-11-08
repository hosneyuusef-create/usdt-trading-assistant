## Project Charter for Autonomous Codex Agent

This document is a single source of truth for the **Codex v5 autonomous agent** that will rebuild the USDT Trading Assistant from scratch and deliver it to “production-ready, zero-known-defect” state. You must treat this charter as law: read it entirely before touching code, follow it verbatim, and keep it updated through verifiable artefacts, logs, tests, and documentation. You are empowered to make every technical decision needed to reach the goal—do not ask the operator for clarification. When you encounter ambiguity, conflicts, or missing data, resolve them yourself, document the resolution, and keep moving. Your delivery must be **self-testing, self-healing, observable, auditable, and exhaustively documented**.

---

### 1. Mission Statement

Build an end‑to‑end production-grade USDT trading assistant (Telegram bot + backend + frontend ops console) that:

1. Runs entirely on PostgreSQL (no sqlite/sql.js remnants).
2. Provides real dual-control approvals, MFA, settlement workflows with feature flags, robust metrics/alerting, CI/CD with health/rollback, dev parity, dependency governance, and complete documentation packs.
3. Is fully testable (unit/integration/e2e/perf), self-validating (automated migrations/tests in CI), and observable (metrics/logs/alerting with documented runbooks).
4. Ships with final reports showing 0 failing tests/lints, instructions for ops, and explicit statements on remaining risks (ideally none).

You are the **sole engineer, tester, tech writer, and release manager**. No follow-up questions—solve every gap yourself.

---

### 2. Global Duties (apply to every phase)

- **Autonomy & Self-Correction:** Detect inconsistencies or missing info, decide on the fix, implement it, document the rationale. If a regression occurs, bisect and self-correct.
- **Observability:** Instrument code (metrics, logs, traces) and provide Prometheus metrics + alerting runbooks.
- **Testing:** Maintain automated migrations/tests. Every module touched must have appropriate unit/integration/e2e coverage. Performance tests must demonstrate ≤120 s total runtime for stress cases.
- **Documentation:** Keep README + docs (RTM, personas, risk register, coverage analysis) in sync with reality. Every feature/flag/runbook needs written guidance.
- **Reporting:** Maintain a running `REPORT.md` (create if missing) that tracks per-phase progress, commands run, logs, test outcomes, and remaining risks. Final summary must enumerate files changed per phase, tests run, logs, env instructions, feature-flag statuses, and risk disposition.
- **Version Control Hygiene:** Work in meaningful commits (even if local). Avoid dangling half-finished changes; keep diffs reviewable. Never regress previously green tests.
- **Security & Compliance:** Enforce dependency scanning, npm audit gates, secure secrets handling, JWT/MFA policies, and RBAC. Document security posture.
- **IDE/Workspace Assumptions:** You receive no additional files beyond this repo. Generate everything needed (configs, scripts, assets) yourself.

---

### 3. Functional Requirements Overview

1. **Backend**
   - Fastify-based API + Telegram bot.
   - PostgreSQL via Knex (or Prisma) with full migration history (up/down). No sql.js anywhere.
   - Domains: Users, Dual Control, RFQ/Quotes/Fills, Settlements, Wallet, SLA/Spread/Alerts, MFA, Notifications, Metrics.
   - Async repositories/services with proper error handling, logging, audit trails.
   - Feature flag `AUTO_SETTLEMENT_ENABLED` controlling settlement workflow.
   - Metrics: RFQ volume, settlement queues, flagged_off counts, wallet balances, alert rates, error gauges, queue lengths.
   - Alerting: configurable thresholds, debounce/rate limit, runbook.

2. **Frontend (Ops console)**
   - Approvals UI with dual-control (reason + secondary approver).
   - Displays errors from server, shows metrics/alert statuses.
   - Tests for ops workflows (e.g. `ops-approval.spec.ts`).

3. **CI/CD**
   - Workflow: lint → backend test → frontend test → docs lint → build/publish → security scan → deploy → health check → rollback on failure.
   - Docker Compose deploy with post-deploy `/health` check and automatic rollback.
   - Stage logs must be clear and captured in final report.

4. **Docs**
   - README: architecture diagram (ASCII allowed), DB instructions (dev/prod/backup), migration commands, troubleshooting (ESM, proxy, wallet), dev env commands.
   - `docs/RTM.md`, `docs/personas.md`, `docs/risk_register.md`, `docs/TEST_COVERAGE_ANALYSIS.md` all rewritten with Version/Owner/Last Reviewed and the required structures.
   - Alerting runbook listing Alert, Threshold, Action, Owner.
   - Markdownlint config + zero lint warnings.

5. **Dev Environment Parity**
   - Backend `npm run dev` uses `tsx watch`.
   - Frontend proxy points to `127.0.0.1:9090`.
   - `npm run dev:smoke` (or documented equivalent) spins up both services and performs a health/login smoke test, logging the results.
   - README documents dev/prod/proxy troubleshooting.

6. **Dependency & Security Management**
   - Dependabot/Renovate config covering backend/frontend npm (weekly at minimum).
   - CI stage for `npm audit --prod` and `npm audit --dev`; fail on High/Critical.
   - Lockfiles updated post-migration.
   - Document dependency policy in README/docs.

7. **Final Acceptance (Phase 9)**
   - Commands executed:  
     `cd backend && npm run lint && npm test`  
     `cd frontend && npm run build && npm test`  
     `markdownlint README.md docs/*.md`
   - Final report lists:
     * Files changed per phase.
     * Tests run (command + significant output).
     * Feature flag statuses (dev/prod).
     * Remaining issues (should be zero; if not, justify with mitigation plan).
     * Explicit guarantee of zero known defects or list with mitigation/plan.

---

### 4. Phase Breakdown (strict order)

#### Phase 0 – Preparation
1. Record `git status -sb`.
2. Log versions for Node, npm, PostgreSQL, other critical tools.
3. Ensure every CLI invocation includes working directory and capture relevant output in `REPORT.md`.

#### Phase 1 – PostgreSQL Migration
Scope: `backend/src/database/**/*`, `backend/src/domain/**/*`, `backend/src/server/**/*`, `backend/tests/**/*`, `backend/scripts/seed-users.mjs`, `backend/package.json`, `.env.example`, `README`, `backend/migrations/**/*`, and any other files required for a complete migration.

Tasks:
1. Design comprehensive schema (Users, RFQs, Quotes/Fills, Settlements, Audit, DualControl, SLA, Spread, API Keys, MFA, Notifications, CSRF tokens, active LPs, etc.).
2. Replace sql.js with PostgreSQL using Knex/Prisma. All repositories async/await.
3. Update every domain/service/router/test/seed to async.
4. Update seeds/scripts, `.env.example`, README (DB instructions, migrations).
5. Remove all sql.js references, legacy SQLite docs.
6. Tests:  
   - `cd backend && npm run migrate:dev`  
   - `cd backend && DB_URL=postgres://... npm test` (full suite)  
   - Manual smoke: create & approve user, verify row in PostgreSQL (document query/output).

Checkpoint Checklist:
- Zero sql.js imports.
- All migrations have up/down.
- All repos/domains/servers async and wired to PostgreSQL.
- Seeds validated on PostgreSQL.
- README DB section updated (dev/prod/backup).
- Tests above recorded with logs/screenshots if relevant.

#### Phase 2 – Dual-Control Enhancements
Scope: `backend/src/domain/user.ts`, dual-control modules/migrations, `backend/src/server/app.ts` and related routes, `frontend/src/pages/ops/index.js`, tests, docs/README sections.

Tasks:
1. Add DB columns `approval_reason`, `secondary_approver_id`, `secondary_approved_at` (with data migration).
2. Enforce reason + secondary approver in domain + API + UI with validation & audit logging.
3. Update `/users/:id/approve` & `/reject` APIs.
4. Frontend form requires reason + secondary approver (with error handling).
5. Tests: backend dual-control scenarios + frontend submission/e2e.
6. Docs: dual-control process, selecting second approver.

Checklist:
- No approval path without reason/secondary approver.
- Schema migrated, UI handles server errors.
- Audit log captures reason & secondary approver.
- Tests: `cd backend && npm test -- dual-control.test.ts`, `cd frontend && npm test -- ops-approval.spec.ts`, manual POST without reason ⇒ 400 documented.

#### Phase 3 – Settlement Feature Flag & Performance
Scope: `backend/src/domain/{rfq,settlement,wallet,metrics,alerting}.ts`, configs, performance tests, README.

Tasks:
1. Add `AUTO_SETTLEMENT_ENABLED` flag.
2. Flag OFF: create `flagged_off` records, emit metrics/alerts, ensure queue doesn’t grow indefinitely.
3. Flag ON: full settlement workflow (wallet enabled, robust error handling).
4. Make `applyQuote` non-blocking/batching for lower latency.
5. Split performance test: flag-off + flag-on, using mock wallet. Total runtime ≤120 s.
6. Add metrics/alerts for queue length, flagged count, etc.
7. README/docs: describe flag behavior & activation instructions.

Checklist/Tests:
- No silent returns; reasons logged.
- Queue drained under flag-off.
- `/metrics` exposes new gauges.
- Alerts throttled.
- Tests: `cd backend && npm test -- tests/performance/stress-test.test.ts` (both modes), `curl /metrics` outputs documented, manual flag=false scenario increases flagged metric.
- Performance log ≤120000 ms recorded.

#### Phase 4 – CI/CD with Health & Rollback
Scope: `.github/workflows/ci.yml`, `docker-compose.yml`, README, frontend smoke test.

Tasks:
1. Rebuild workflow pipeline (lint → backend test → frontend test → docs lint → build/push → security scan → deploy).
2. Ensure frontend has real tests or add smoke test.
3. Deploy stage: run `docker compose up`, then health check `/health`. On failure, trigger rollback to previous image automatically.
4. README: pipeline explanation, CI variables, rollback steps.
5. Document stage logs in final report.

Checklist:
- No duplicate workflows.
- Health check & rollback automatic.
- Frontend tests mandatory for success.
- README includes pipeline table + rollback instructions.
- Tests: run pipeline locally (act) for lint/test stages, simulate manual health check.

#### Phase 5 – Documentation & Architecture
Scope: `docs/RTM.md`, `docs/personas.md`, `docs/risk_register.md`, `docs/TEST_COVERAGE_ANALYSIS.md`, README.

Tasks:
1. Rewrite each doc with Version, Last Reviewed, Owner. Include required structures (RTM mapping, persona scenarios, risk table, coverage percentages/gaps/action plan).
2. README: architecture diagram (ASCII or linked image), dev/prod/migration/health/troubleshooting (include ESM, proxy, wallet errors).
3. Add/configure markdownlint; run until zero violations.

Checklist/Tests:
- `markdownlint README.md docs/*.md` passes.
- Text readable (UTF-8), links point to actual artefacts.
- Manual review documented.

#### Phase 6 – Dev Environment Parity
Scope: backend package scripts, frontend `vite.config.js`, README dev section, scripts.

Tasks:
1. Backend `npm run dev` uses `tsx watch`; remove ts-node-dev references.
2. Frontend proxy targets `127.0.0.1:9090`; document in README.
3. Add `npm run dev:smoke` (or doc’d equivalent) spinning up backend+frontend and executing health/login smoke, logging results.
4. README troubleshooting for ESM/proxy errors.
5. Manual verification logs: `npm run dev` back & front, plus login smoke.

Checklist:
- Backend dev server runs without errors.
- Frontend proxy works (no errors).
- README dev instructions complete.
- Tests/logs recorded for manual runs.

#### Phase 7 – Dependency & Security Management
Scope: package manifests, lockfiles, `.github/dependabot.yml` or `renovate.json`, CI workflow.

Tasks:
1. Configure Dependabot/Renovate for backend+frontend npm (≥ weekly).
2. CI stage running `npm audit --prod` + `npm audit --dev`, failing on High/Critical.
3. Update lockfiles after DB migration.
4. Document dependency strategy in README/docs.

Checklist/Tests:
- Automation config committed.
- Audit stage integrated in CI with logged output.
- Manual `npm audit` run recorded.
- README/docs describe policy.

#### Phase 8 – Alerting & Monitoring
Scope: `backend/src/domain/alerting.ts`, `metrics.ts`, alert routes, README/runbook.

Tasks:
1. Move alert thresholds to config (no hardcodes).
2. Add debounce/rate limit per alert type per window.
3. `/metrics` exposes gauges for error rate, settlement queue length, flagged_off, wallet balance, and any introduced KPI.
4. README/runbook: table of Alert, Threshold, Action, Owner.

Tests:
- `cd backend && npm test -- alerting.test.ts`.
- Manual alert simulation proving throttling.
- `curl /metrics` showing new gauges.

Acceptance:
- Tests green.
- Gauges observable.
- Runbook present.

#### Phase 9 – Finalization
1. Run required commands (Section 3.7).
2. Update `REPORT.md` with final summary (files per phase, tests, logs, feature flags, open issues).
3. Provide explicit statement confirming zero known defects (or enumerate with mitigation plan).

Deliverable: final repo state ready for audit, all docs/tests/logs in place, `REPORT.md` referencing evidence.

---

### 5. Engineering Principles & Constraints

- **Atomicity:** Treat each phase as gate-controlled; do not proceed until its tests/docs pass.
- **Idempotence:** Scripts (migrations, seeds, CI tasks) must be rerunnable without manual cleanup.
- **Recoverability:** Provide rollback strategies (DB migrations, deployments).
- **Security-first:** Enforce JWT secret checks, MFA, RBAC, audit logs, sanitized logs, secrets via env.
- **Performance:** Stress tests prove the system handles 600 RPM with feature flags toggled, ≤120 s runtime.
- **UX:** Ops UI must surface server errors, validation states, and approval metadata clearly.
- **Documentation-as-code:** Keep diagrams and docs version-controlled; mention update instructions for future maintainers.

---

### 6. Final Output Expectations

Upon completion, the repository must contain:
1. Working backend/frontend with full PostgreSQL support and all phases satisfied.
2. Passing test and lint suites (backend/frontend/docs) with reproducible commands.
3. Up-to-date README + docs + runbooks + coverage analyses.
4. CI/CD pipeline files, Dependabot/Renovate, docker-compose with health/rollback.
5. Observability stack (metrics/alerts) plus manual verification logs.
6. `REPORT.md` summarizing everything (phases, tests, logs, feature flags, risks).
7. `AGENTS.md` (this file) and any new meta-docs kept updated to reflect actual behavior.

Failure to deliver any checklist item blocks completion; you must self-verify and self-heal before considering the project done.

---

### 7. How to Work

1. **Plan → Execute → Verify → Document** for each phase.
2. Commit granularly (phase or feature level), referencing tests/logs in commit messages when helpful.
3. Keep `REPORT.md` in sync after each major action (command run, tests, manual verifications).
4. When unsure, choose the option that maximizes reliability, observability, and maintainability—then document why.
5. Treat this charter as “living”—if you must deviate for a compelling reason, document both the deviation and justification in `REPORT.md` plus relevant docs.

You now have full authority and responsibility. Begin by resetting environment awareness (Phase 0), then progress through the phases, ensuring every acceptance criterion is met and documented. Do not stop until the system reaches the defined “production-ready, zero-known-defect” state.

Good luck.

