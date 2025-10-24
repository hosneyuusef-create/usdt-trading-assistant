# Provider Eligibility Policy – Stage 11

## Overview
- Purpose: define the minimum criteria a provider must meet to receive RFQ notifications and participate in settlement workflows.
- Scope: applies to all providers registered via `src/backend/provider` and enforced by the Stage 11 eligibility engine (marahel_utf8.txt:195, marahel_utf8.txt:201).
- Dependencies: domain model (artefacts/domain_glossary.md:6), database schema (`db/schema/database_schema_v1.sql:32`), verification policies for customer tiers (`artefacts/Verification_Policies.json`).

## Eligibility Thresholds
- **Minimum performance score:** 70 (configurable through environment variable `PROVIDER_MIN_SCORE`).
- **Minimum collateral:** 200,000,000 IRR (configurable via `PROVIDER_MIN_COLLATERAL`).
- **Active flag:** providers must be marked `is_active=True` to remain eligible.
- Optional overrides should be recorded in change control documentation and reflected in the assumption log if thresholds are temporary (marahel_utf8.txt:206).

## Evaluation Workflow
1. Provider registers or updates details through `/provider/register`.
2. Eligibility engine evaluates:
   - Score >= configured minimum.
   - Collateral >= configured minimum.
   - Provider active status.
3. Decision recorded as `EligibilitySummary` on the response and stored for reuse.
4. Every RFQ broadcast invokes `ProviderRegistry.filter_for_rfq` which logs `rfq_eligibility_evaluated` entries for audit.

## Logging and Audit
- Logger: `usdt.provider`.
- Events:
  - `provider_registered` – emitted after each registration/update.
  - `provider_eligible` – debug record for satisfied thresholds.
  - `rfq_eligibility_evaluated` – info record covering RFQ filtering decisions (marahel_utf8.txt:201, marahel_utf8.txt:204).
- Logs include provider id, telegram id, eligibility result, failure reasons, and thresholds.

## Maintenance
- Threshold changes require:
  - Updating environment variables or deployment configuration.
  - Documenting rationale in this policy and `artefacts/stage_completion_checklist.md`.
  - Creating/closing assumptions in `artefacts/assumptions_log.md` if values are temporary.
- Score update automation is planned for Stage 20 (marahel_utf8.txt:203). Until then, manual score adjustments follow this policy.

## Testing
- Unit tests: `tests/test_provider_management.py` validates registration, eligibility evaluation, and RFQ filtering.
- Stage evidence stored in `artefacts/test_reports/M11_provider_tests.md`.
- CI integration: future Stage 24 test suites must include provider eligibility coverage (marahel_utf8.txt:202, marahel_utf8.txt:426).
