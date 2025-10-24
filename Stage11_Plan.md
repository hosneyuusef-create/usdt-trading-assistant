# Stage 11 - Provider Management Work Plan

## Objective
- Implement the provider management module under `src/backend/provider` and deliver the eligibility policy artefact mandated by Stage 11 (marahel_utf8.txt:195, marahel_utf8.txt:198).
- Enforce minimum score 70 and collateral 200,000,000 IRR when broadcasting RFQs, with auditable logging (marahel_utf8.txt:201, marahel_utf8.txt:204).

## Prerequisites and Readiness Tasks
- Package the offline pytest toolchain and fix the PowerShell integration script parameter so Stage 1 assumptions AL-001 through AL-003 can close (artefacts/stage_completion_checklist.md:22; scripts/tests/run_integration_tests.ps1:1; artefacts/assumptions_log.md:4).
- Install and verify RabbitMQ Windows Service to remove the warning observed during the Zero-to-Dev run (artefacts/zerotodev_execution.log:26).
- Capture pending lessons learned for stages 1 to 10 to keep governance artefacts current (artefacts/stage_completion_checklist.md:19, artefacts/stage_completion_checklist.md:175).

## Inputs and Reference Material
- Domain definitions for Provider and ProviderScoreSnapshot (artefacts/domain_glossary.md:6).
- Database schema for providers and scoring snapshots (db/schema/database_schema_v1.sql:32, db/schema/database_schema_v1.sql:201).
- Existing module layout and dependency pattern demonstrated by the customer module (src/backend/README.md:9; src/backend/customer/router.py:11; src/backend/customer/service.py:42).
- Secrets policy for credential naming and retrieval (artefacts/Secrets_Management.md:7, artefacts/Secrets_Management.md:12).

## Work Breakdown
1. **Module Scaffold**
   - Create `__init__.py`, `router.py`, `schemas.py`, and `service.py` under `src/backend/provider`, mirroring FastAPI patterns from the customer module (src/backend/core/app.py:12).
   - Register provider routes in `core/app.py` and expose dependency injection helpers.
2. **Eligibility Engine**
   - Load policy thresholds from configuration or a dedicated JSON/MD source and compute eligibility based on score and collateral.
   - Capture audit records using structlog to align with existing logging practices (src/backend/customer/service.py:47).
3. **`artefacts/Provider_Eligibility.md`**
   - Document thresholds, evaluation algorithm, exception handling, escalation, and maintenance workflow with clear linkage to RTM IDs.
4. **RFQ Broadcast Filter**
   - Integrate eligibility checks into the RFQ dispatch path (placeholder service if RFQ module is pending) so only qualified providers receive notifications, satisfying Stage 11 acceptance criteria (marahel_utf8.txt:201).
5. **Testing**
   - Unit tests for eligibility pass/fail cases and audit logging.
   - Integration test using seeded provider data (tests/data/seed/sample_data.sql:1) to validate filter behaviour.
   - Update automated scripts so new tests run under `scripts/tests/run_unit_tests.ps1` and `scripts/tests/run_integration_tests.ps1`.
6. **Documentation and Governance**
   - Update `artefacts/stage_completion_checklist.md` with Stage 11 outputs, test evidence, and lessons learned.
   - Log any new assumptions or decisions in `artefacts/assumptions_log.md` immediately.

## Deliverables
- Backend provider module committed in `src/backend/provider`.
- `artefacts/Provider_Eligibility.md` with approval-ready policy content.
- Updated test suites and execution evidence stored in `artefacts/test_reports/`.
- Stage 11 checklist entries completed with links and recorded lessons.

## Risks and Mitigations
- **Missing RabbitMQ service:** install before Stage 11 work to prevent integration blockers (artefacts/zerotodev_execution.log:26).
- **Unclosed Stage 1 assumptions:** prioritize dependency packaging and script fixes so automated tests are reliable for Stage 11 validation (artefacts/stage_completion_checklist.md:22).
- **Policy drift:** maintain a single source of truth in the eligibility artefact and reference it from code to reduce divergence.

## Exit Criteria
- Eligibility-aware provider endpoints respond correctly and emit structured logs.
- RFQ broadcast logic filters out unqualified providers in tests and manual walkthroughs.
- `artefacts/Provider_Eligibility.md` is versioned, reviewed, and cross-referenced in RTM.
- Stage 11 checklist rows show "Checked" status for outputs, tests, assumptions, and lessons learned.
