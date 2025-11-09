# Risk Register

- **Version:** 1.0.0  
- **Owner:** Codex Autonomous Agent  
- **Last Reviewed:** 2025-11-08

| Risk ID | Description | Impact | Likelihood | Mitigation / Controls | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| RS-01 | AUTO_SETTLEMENT disabled unintentionally, leaving fills unprocessed | High (trades stuck) | Medium | Flag metrics + `auto_settlement_disabled` alert, runbook in `docs/settlement_flag.md`, CI tests covering flag states | Platform Engineer | Mitigated |
| RS-02 | Dual-control approvals missing rationale/second approver | High (policy breach) | Low | Schema constraints, backend validation, frontend UX + automated tests | Ops Approver Lead | Mitigated |
| RS-03 | Postgres credentials/DB not backed up | Medium | Medium | README backup procedure, scheduled `pg_dump`, infra ticket to automate snapshots | Platform Engineer | Open (pending automation) |
| RS-04 | Dependencies introduce high-severity vulnerabilities | High | Medium | CI `npm audit --audit-level=high` gates, Dependabot/renovate config (Phase 7), manual audits logged in REPORT | Security Lead | Mitigated |
| RS-05 | Docker deploy fails silently, leaving unhealthy release live | High | Low | CI docker stage with `/health` probe + automatic rollback, evidence in Actions Run 19191541763 | Platform Engineer | Mitigated |
| RS-06 | Wallet ledger drift due to missed metrics refresh | Medium | Medium | `refreshWalletMetrics` after every movement, Prometheus `wallet_balance` gauge, manual reconciliation doc (README troubleshooting) | Treasury Ops | Mitigated |
