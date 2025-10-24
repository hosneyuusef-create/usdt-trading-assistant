import os
import re
import psycopg2

conn = psycopg2.connect(
    host=os.environ.get('PGHOST', 'localhost'),
    port=os.environ.get('PGPORT', '5432'),
    user=os.environ.get('PGUSER', 'postgres'),
    password=os.environ.get('PGPASSWORD'),
    dbname=os.environ.get('PGDATABASE', 'usdt_trading')
)
conn.autocommit = True
cur = conn.cursor()

# Cleanup existing sample data
cur.execute("TRUNCATE TABLE provider_score_snapshots, config_versions, notification_events, notification_templates, dispute_actions, evidence, disputes, settlement_legs, settlements, awards, quotes, rfqs, admin_users, providers, customers RESTART IDENTITY CASCADE;")

# Seed customers
cur.execute("""
INSERT INTO customers (customer_id, telegram_id, kyc_tier, wallet_alias, email, status)
SELECT uuid_generate_v4(), 1000000000 + gs, CASE WHEN gs % 3 = 0 THEN 'premium' WHEN gs % 3 = 1 THEN 'advanced' ELSE 'basic' END,
       CONCAT('wallet_', gs), CONCAT('customer', gs, '@example.com'), 'active'
FROM generate_series(1, 2000) gs;
""")

# Seed providers
cur.execute("""
INSERT INTO providers (provider_id, telegram_id, score, collateral_amount, status, max_capacity)
SELECT uuid_generate_v4(), 2000000000 + gs, 80 + (gs % 20), 500000 + gs * 100, CASE WHEN gs % 5 = 0 THEN 'suspended' ELSE 'active' END, 100000 
FROM generate_series(1, 500) gs;
""")

# Seed admin users
cur.execute("""
INSERT INTO admin_users (admin_id, email, role, password_hash)
SELECT uuid_generate_v4(), CONCAT('admin', gs, '@example.com'), CASE WHEN gs % 2 = 0 THEN 'ops' ELSE 'compliance' END, 'hashed'
FROM generate_series(1, 20) gs;
""")

# Seed RFQs
cur.execute("""
INSERT INTO rfqs (rfq_id, customer_id, rfq_type, network, amount, min_fill, status, settlement_order, expiry_at)
SELECT uuid_generate_v4(), c.customer_id,
       CASE WHEN gs % 2 = 0 THEN 'buy' ELSE 'sell' END,
       CASE WHEN gs % 3 = 0 THEN 'TRC20' WHEN gs % 3 = 1 THEN 'BEP20' ELSE 'ERC20' END,
       1000 + (gs * 10), 500, CASE WHEN gs % 5 = 0 THEN 'awarded' ELSE 'open' END,
       CASE WHEN gs % 4 = 0 THEN 'usdt_first' ELSE 'fiat_first' END,
       NOW() + (gs % 12) * INTERVAL '10 minutes'
FROM generate_series(1, 2000) gs
JOIN customers c ON c.telegram_id = 1000000000 + gs;
""")

# Seed Quotes (approx 10000)
cur.execute("""
INSERT INTO quotes (quote_id, rfq_id, provider_id, unit_price, capacity, fee, status, expires_at)
SELECT uuid_generate_v4(), r.rfq_id, p.provider_id,
       420000 + (random()*1000), 1000 + (random()*500), 10, CASE WHEN gs % 7 = 0 THEN 'expired' ELSE 'submitted' END,
       NOW() + INTERVAL '30 minutes'
FROM (
    SELECT rfq_id, row_number() OVER () AS rn FROM rfqs
) r
JOIN (
    SELECT provider_id, row_number() OVER () AS rn FROM providers
) p ON (r.rn + p.rn) % 5 = 0
JOIN generate_series(1, 10000) gs ON TRUE
LIMIT 10000;
""")

# Seed Awards (subset)
cur.execute("""
INSERT INTO awards (award_id, rfq_id, quote_id, selection_mode, awarded_amount)
SELECT uuid_generate_v4(), r.rfq_id, q.quote_id,
       CASE WHEN row_number() OVER () % 2 = 0 THEN 'auto' ELSE 'manual' END,
       q.capacity
FROM rfqs r
JOIN quotes q ON q.rfq_id = r.rfq_id
WHERE r.status = 'awarded'
LIMIT 1500;
""")

# Seed Settlements
cur.execute("""
INSERT INTO settlements (settlement_id, award_id, status, sla_deadline, retry_count)
SELECT uuid_generate_v4(), a.award_id,
       CASE WHEN row_number() OVER () % 4 = 0 THEN 'completed'
            WHEN row_number() OVER () % 4 = 1 THEN 'pending'
            WHEN row_number() OVER () % 4 = 2 THEN 'disputed'
            ELSE 'expired' END,
       NOW() + INTERVAL '2 hours', 0
FROM awards a;
""")

# Seed Settlement Legs
cur.execute("""
INSERT INTO settlement_legs (settlement_leg_id, settlement_id, quote_id, leg_type, amount, status, due_at)
SELECT uuid_generate_v4(), s.settlement_id, a.quote_id,
       CASE WHEN gs % 2 = 0 THEN 'fiat' ELSE 'usdt' END,
       500 + gs * 5,
       CASE WHEN gs % 3 = 0 THEN 'completed' ELSE 'pending' END,
       NOW() + INTERVAL '1 hour'
FROM settlements s
JOIN awards a ON a.award_id = s.award_id
JOIN generate_series(1,2) gs ON TRUE;
""")

# Seed Disputes for some settlements
cur.execute("""
INSERT INTO disputes (dispute_id, settlement_id, claimant_customer_id, respondent_provider_id, reason, status)
SELECT uuid_generate_v4(), s.settlement_id, r.customer_id, q.provider_id,
       'Late settlement', CASE WHEN row_number() OVER () % 2 = 0 THEN 'resolved' ELSE 'open' END
FROM settlements s
JOIN awards a ON a.award_id = s.award_id
JOIN rfqs r ON r.rfq_id = a.rfq_id
JOIN quotes q ON q.quote_id = a.quote_id
WHERE s.status IN ('disputed','expired')
LIMIT 300;
""")

# Seed Evidence linked to disputes and settlements
cur.execute("""
INSERT INTO evidence (evidence_id, settlement_id, dispute_id, evidence_type, storage_url, hash, metadata)
SELECT uuid_generate_v4(), s.settlement_id, d.dispute_id, 'screenshot',
       CONCAT('https://evidence/', d.dispute_id), md5(random()::text), '{"type":"screenshot"}'::jsonb
FROM disputes d
JOIN settlements s ON s.settlement_id = d.settlement_id;
""")

# Seed Dispute actions
cur.execute("""
INSERT INTO dispute_actions (action_id, dispute_id, admin_id, actor_type, notes, action_taken)
SELECT uuid_generate_v4(), d.dispute_id, au.admin_id, 'admin', 'Reviewed dispute', 'reviewed'
FROM disputes d
JOIN admin_users au ON TRUE
LIMIT 300;
""")

# Seed notification templates & events
cur.execute("""
INSERT INTO notification_templates (template_id, channel, version, body)
SELECT uuid_generate_v4(), 'telegram', gs, 'Template body'
FROM generate_series(1,5) gs;
""")
cur.execute("""
INSERT INTO notification_events (event_id, template_id, related_type, related_id, status, attempts)
SELECT uuid_generate_v4(), nt.template_id, 'settlement', s.settlement_id, 'sent', 1
FROM notification_templates nt
JOIN settlements s ON TRUE
LIMIT 1000;
""")

# Seed config versions & provider score snapshots
cur.execute("""
INSERT INTO config_versions (config_id, json_payload, approved_by, notes)
SELECT uuid_generate_v4(), '{"settlement_order":"fiat_first"}'::jsonb, au.admin_id, 'Initial config'
FROM admin_users au
LIMIT 3;
""")
cur.execute("""
INSERT INTO provider_score_snapshots (snapshot_id, provider_id, score, collateral_balance)
SELECT uuid_generate_v4(), provider_id, score, collateral_amount
FROM providers;
""")

cur.execute('ANALYZE');

# Performance queries
results = {}
queries = [
    ("quotes_for_open_rfq",
     "EXPLAIN ANALYZE SELECT q.quote_id FROM quotes q JOIN rfqs r ON q.rfq_id = r.rfq_id WHERE r.status = 'open' AND q.status = 'submitted' ORDER BY q.created_at DESC LIMIT 20"),
    ("disputes_lookup",
     "EXPLAIN ANALYZE SELECT d.dispute_id FROM disputes d JOIN settlements s ON s.settlement_id = d.settlement_id WHERE d.status = 'open' ORDER BY d.opened_at DESC LIMIT 20"),
    ("notification_queue",
     "EXPLAIN ANALYZE SELECT event_id FROM notification_events WHERE status = 'queued' ORDER BY created_at DESC LIMIT 50")
]

for name, query in queries:
    cur.execute(query)
    plan = "\n".join(row[0] for row in cur.fetchall())
    match = re.search(r"Execution Time: ([0-9.]+) ms", plan)
    if not match:
        raise AssertionError(f"Could not parse execution time for {name}\n{plan}")
    exec_time = float(match.group(1))
    if exec_time >= 50:
        raise AssertionError(f"Query {name} exceeded threshold: {exec_time} ms\n{plan}")
    results[name] = (exec_time, plan)

with open('artefacts/SchemaPerformanceReport.md', 'w', encoding='utf-8') as fh:
    fh.write('# Schema Performance Report – Stage 5\n\n')
    fh.write('- تاریخ: 2025-10-23\n')
    fh.write('- داده نمونه: 2000 Customer، 500 Provider، ~10000 Quote\n')
    fh.write('- حداکثر زمان قابل قبول: 50ms\n\n')
    for name, (exec_time, plan) in results.items():
        fh.write(f'## {name}\n')
        fh.write(f'- Execution Time: {exec_time:.3f} ms\n')
        fh.write('```\n')
        fh.write(plan + '\n')
        fh.write('```\n\n')

print('Performance tests passed:', ', '.join(f"{k}={v[0]:.2f}ms" for k,v in results.items()))
cur.close()
conn.close()
