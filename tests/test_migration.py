import os
import psycopg2

REQUIRED_TABLES = [
    'customers','providers','admin_users','rfqs','quotes','awards','settlements',
    'settlement_legs','disputes','evidence','dispute_actions','notification_templates',
    'notification_events','config_versions','provider_score_snapshots'
]

REQUIRED_INDEXES = 30

conn = psycopg2.connect(
    host=os.environ.get('PGHOST', 'localhost'),
    port=os.environ.get('PGPORT', '5432'),
    user=os.environ.get('PGUSER', 'postgres'),
    password=os.environ.get('PGPASSWORD'),
    dbname=os.environ.get('PGDATABASE', 'usdt_trading')
)
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
existing = {row[0] for row in cur.fetchall()}
missing = [t for t in REQUIRED_TABLES if t not in existing]
if missing:
    raise AssertionError(f"Missing tables: {missing}")

cur.execute("""
    SELECT COUNT(1)
    FROM pg_indexes
    WHERE schemaname = 'public'
""")
index_count = cur.fetchone()[0]
if index_count < REQUIRED_INDEXES:
    raise AssertionError(f"Expected at least {REQUIRED_INDEXES} indexes, found {index_count}")

print(f"Migration test passed. Tables: {len(REQUIRED_TABLES)}; Index count: {index_count}")
cur.close()
conn.close()
