# AUTO_SETTLEMENT Feature Flag Runbook

Version: 0.1.0  
Owner: Trading Platform Engineering  
Last Reviewed: 2025-11-07

## Overview

`AUTO_SETTLEMENT_ENABLED` gates whether RFQ fills are settled automatically. Toggle it via:

1. Environment variable (`AUTO_SETTLEMENT_ENABLED=true|false`)
2. `feature_flags` table entry (`key = 'AUTO_SETTLEMENT_ENABLED'`)

When disabled, fills are recorded but no settlement jobs are queued. Every attempt is logged in
`settlement_flagged_events`, metrics increment, and an alert is emitted.

## Flag OFF Behavior

- `acceptQuote` calls `scheduleSettlementWorkItem`, which detects the flag and:
  - Inserts a row into `settlement_flagged_events` with metadata (RFQ, quote, fill, notional).
  - Increments Prometheus metrics:
    - `flagged_off_total`
    - `settlement_flagged_total{reason="AUTO_SETTLEMENT_DISABLED"}`
    - `auto_settlement_status` (set to `0`)
  - Emits alert rule `auto_settlement_disabled` (debounced 60 s)
- No rows are added to `settlement_jobs`, so queue length remains bounded.

## Flag ON Behavior

- Settlements are inserted with status `queued` and a `settlement_jobs` entry is created.
- Metrics updated:
  - `settlement_queue_size`
  - `auto_settlement_status=1`
- Wallet movements occur when `markJobSucceeded` runs (e.g., via settlement worker).

## Metrics & Alerting

| Metric | Description |
| --- | --- |
| `auto_settlement_status` | `1` when enabled, `0` when disabled |
| `settlement_flagged_total{reason}` | Counter of flagged events |
| `flagged_off_total` | Gauge of outstanding flagged events |
| `settlement_queue_size` | Number of queued jobs |

Alert rule `auto_settlement_disabled` watches `auto_settlement_status` and notifies the owner when the metric drops to
zero.

## Operational Commands

- Toggle via DB:

  ```sql
  insert into feature_flags(key, is_enabled, created_at, updated_at)
  values ('AUTO_SETTLEMENT_ENABLED', true, now(), now())
  on conflict (key) do update
    set is_enabled = excluded.is_enabled,
        updated_at = now();
  ```

- Check flagged backlog:

  ```sql
  select * from settlement_flagged_events
  order by created_at desc
  limit 20;
  ```

- Requeue flagged events after enabling auto settlement (ad-hoc):

  ```sql
  insert into settlements (id, fill_id, status, retry_count, metadata, created_at, updated_at)
  select gen_random_uuid(), fill_id, 'queued', 0, metadata, now(), now()
  from settlement_flagged_events;

  delete from settlement_flagged_events;
  ```

## Testing

- Automated unit tests:
  - `npm test -- tests/settlement-flag.test.ts`
  - `npm test -- tests/performance/settlement-stress.test.ts`
- Manual flag-off verification:

  ```bash
  AUTO_SETTLEMENT_ENABLED=false npm run dev
  npx tsx scripts/manual-smoke.ts
  psql ... -c "SELECT count(*) FROM settlement_flagged_events;"
  ```

## Performance Expectations

`tests/performance/settlement-stress.test.ts` ensures 40 flagged settlements and 40 queued settlements complete in under
120 seconds using synchronous scheduling. The test also validates the `AUTO_SETTLEMENT_DISABLED` alert path and queue
metrics.
