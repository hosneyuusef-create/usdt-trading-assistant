# Stakeholder Personas

- **Version:** 1.0.0  
- **Owner:** Codex Autonomous Agent  
- **Last Reviewed:** 2025-11-08

## Persona 1 — Ops Approver

- **Profile:** Senior operations analyst responsible for granting or rejecting access/trade changes;
  lives in Telegram and the ops console.
- **Goals:** Approve legitimate requests quickly, ensure every action includes rationale + secondary
  approver, and keep the audit trail clean.
- **Workflows:** Receives Telegram alert → opens ops console → reviews pending request context →
  records approval reason → selects secondary approver → submits. Uses rejection form with
  justification when needed.
- **Pain Points / Needs:** Wants live backend error feedback, needs list of eligible secondary
  approvers, and expects dual-control policy enforcement without manual policing.

## Persona 2 — Risk & Compliance Lead

- **Profile:** Oversees policy adherence and monitors feature flags, settlement queues, alerting
  thresholds, and audit controls.
- **Goals:** Guarantee AUTO_SETTLEMENT toggles deliberately, prove metrics/alerts exist, and audit
  user approvals for regulators.
- **Workflows:** Checks `/metrics`, reviews `settlement_flagged_events`, exports audit logs,
  toggles feature flags via DB/API when incident response requires it.
- **Pain Points / Needs:** Requires documentation explaining alert thresholds, mitigation steps
  when queues grow, and wallet reconciliation procedures.

## Persona 3 — Platform Engineer / Bot Admin

- **Profile:** Maintains deployment pipeline, Telegram bot tokens, PostgreSQL migrations, and secrets
  management.
- **Goals:** Keep CI/CD green, ensure migrations + docker deploy succeed, manage secrets/backups,
  and provide smoke tooling to ops.
- **Workflows:** Runs `npm run migrate:dev`, monitors GitHub Actions, rotates JWT/Telegram secrets,
  restores databases from backups, and executes `scripts/manual-smoke.ts`.
- **Pain Points / Needs:** Needs clear architecture diagrams, troubleshooting tips for
  ESM/Proxy/Wallet issues, and an auditable log (`REPORT.md`) proving each phase passed.
