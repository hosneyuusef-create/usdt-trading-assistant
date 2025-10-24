# Schema Performance Report – Stage 5

- تاریخ: 2025-10-23
- داده نمونه: 2000 Customer، 500 Provider، ~10000 Quote
- حداکثر زمان قابل قبول: 50ms

## quotes_for_open_rfq
- Execution Time: 1.025 ms
```
Limit  (cost=0.57..2.87 rows=20 width=24) (actual time=0.067..0.866 rows=20 loops=1)
  ->  Nested Loop  (cost=0.57..919.59 rows=8000 width=24) (actual time=0.056..0.629 rows=20 loops=1)
        ->  Index Scan using idx_quotes_status_created on quotes q  (cost=0.29..637.85 rows=10000 width=40) (actual time=0.018..0.128 rows=20 loops=1)
              Index Cond: ((status)::text = 'submitted'::text)
        ->  Memoize  (cost=0.29..0.33 rows=1 width=16) (actual time=0.006..0.007 rows=1 loops=20)
              Cache Key: q.rfq_id
              Cache Mode: logical
              Hits: 19  Misses: 1  Evictions: 0  Overflows: 0  Memory Usage: 1kB
              ->  Index Scan using rfqs_pkey on rfqs r  (cost=0.28..0.32 rows=1 width=16) (actual time=0.011..0.017 rows=1 loops=1)
                    Index Cond: (rfq_id = q.rfq_id)
                    Filter: ((status)::text = 'open'::text)
Planning Time: 2.970 ms
Execution Time: 1.025 ms
```

## disputes_lookup
- Execution Time: 1.083 ms
```
Limit  (cost=0.43..27.09 rows=20 width=24) (actual time=0.063..0.936 rows=20 loops=1)
  ->  Nested Loop  (cost=0.43..200.44 rows=150 width=24) (actual time=0.050..0.712 rows=20 loops=1)
        ->  Index Scan Backward using idx_disputes_status_created on disputes d  (cost=0.15..28.19 rows=150 width=40) (actual time=0.018..0.197 rows=20 loops=1)
              Index Cond: ((status)::text = 'open'::text)
        ->  Index Only Scan using settlements_pkey on settlements s  (cost=0.28..1.15 rows=1 width=16) (actual time=0.008..0.008 rows=1 loops=20)
              Index Cond: (settlement_id = d.settlement_id)
              Heap Fetches: 20
Planning Time: 5.429 ms
Execution Time: 1.083 ms
```

## notification_queue
- Execution Time: 0.115 ms
```
Limit  (cost=5.93..5.93 rows=1 width=24) (actual time=0.043..0.073 rows=0 loops=1)
  ->  Sort  (cost=5.93..5.93 rows=1 width=24) (actual time=0.031..0.049 rows=0 loops=1)
        Sort Key: created_at DESC
        Sort Method: quicksort  Memory: 25kB
        ->  Index Scan using idx_notification_events_status_attempts on notification_events  (cost=0.15..5.92 rows=1 width=24) (actual time=0.016..0.021 rows=0 loops=1)
              Index Cond: ((status)::text = 'queued'::text)
Planning Time: 2.145 ms
Execution Time: 0.115 ms
```

