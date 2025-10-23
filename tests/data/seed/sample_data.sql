BEGIN;

TRUNCATE TABLE user_sessions, system_notifications, audit_logs, disputes, settlement_steps, settlements, awards, quotes, rfqs, admins, providers, customers, users, system_configs, network_configs RESTART IDENTITY CASCADE;

INSERT INTO users (id, phone_number, telegram_id, user_type, verification_level, credit_score, is_active)
VALUES
    ('550e8400-e29b-41d4-a716-446655440001', '09120000001', 'tg_customer_1', 'CUSTOMER', 'BASIC', 72.5, true),
    ('550e8400-e29b-41d4-a716-446655440002', '09120000002', 'tg_provider_1', 'PROVIDER', 'ADVANCED', 88.0, true),
    ('550e8400-e29b-41d4-a716-446655440003', '09120000003', 'tg_admin_1', 'ADMIN', 'ADVANCED', 100.0, true);

INSERT INTO customers (id, user_id, bank_card_number, wallet_address, max_transaction_limit, current_balance)
VALUES
    ('550e8400-e29b-41d4-a716-446655440101', '550e8400-e29b-41d4-a716-446655440001', '5022291071234567', 'TQCustomerWallet001', 1000000.0, 0.0);

INSERT INTO providers (id, user_id, bank_account, wallet_address, collateral_amount, success_rate, total_transactions)
VALUES
    ('550e8400-e29b-41d4-a716-446655440201', '550e8400-e29b-41d4-a716-446655440002', 'IR820540102680020817909002', 'TRProviderWallet001', 250000000.0, 95.0, 140);

INSERT INTO admins (id, user_id, admin_level, permissions)
VALUES
    ('550e8400-e29b-41d4-a716-446655440301', '550e8400-e29b-41d4-a716-446655440003', 'SUPER', '{"approve_award": true, "manage_dispute": true}');

INSERT INTO system_configs (id, config_key, config_value, description, is_active)
VALUES
    ('550e8400-e29b-41d4-a716-446655441001', 'bidding_deadline_minutes', '"10"', 'Default bidding deadline in minutes', true),
    ('550e8400-e29b-41d4-a716-446655441002', 'min_quotes_required', '"1"', 'Minimum valid quotes required', true);

INSERT INTO network_configs (id, network_name, is_active, min_amount, max_amount, min_confirmations)
VALUES
    ('550e8400-e29b-41d4-a716-446655441101', 'TRC20', true, 1.0, 1000000.0, 1),
    ('550e8400-e29b-41d4-a716-446655441102', 'BEP20', true, 1.0, 1000000.0, 3);

INSERT INTO rfqs (id, customer_id, rfq_type, usdt_amount, network, max_price, bidding_deadline, status, special_conditions)
VALUES
    ('550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440101', 'BUY', 100.0, 'TRC20', 85000.0, NOW() + INTERVAL '10 minutes', 'BIDDING_OPEN', '{"split_allowed": true}');

INSERT INTO quotes (id, rfq_id, provider_id, unit_price, capacity, network_fee, status, created_at, updated_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440020', '550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440201', 84000.0, 100.0, 1.0, 'SUBMITTED', NOW(), NOW());

INSERT INTO awards (id, rfq_id, quote_id, selection_method, status, created_at, updated_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440030', '550e8400-e29b-41d4-a716-446655440010', '550e8400-e29b-41d4-a716-446655440020', 'AUTOMATIC', 'PENDING', NOW(), NOW());

INSERT INTO settlements (id, award_id, settlement_type, status, created_at, updated_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440040', '550e8400-e29b-41d4-a716-446655440030', 'BUY', 'IN_PROGRESS', NOW(), NOW());

INSERT INTO settlement_steps (id, settlement_id, step_order, step_type, status, amount, deadline, created_at, updated_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440050', '550e8400-e29b-41d4-a716-446655440040', 1, 'PAYMENT', 'PENDING', 8400000.0, NOW() + INTERVAL '15 minutes', NOW(), NOW());

INSERT INTO disputes (id, settlement_id, complainant_id, dispute_type, status, description, evidence, created_at, updated_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440060', '550e8400-e29b-41d4-a716-446655440040', '550e8400-e29b-41d4-a716-446655440001', 'PAYMENT_ISSUE', 'OPEN', 'Customer reports payment delay', '{"receipt_id": null}', NOW(), NOW());

INSERT INTO audit_logs (id, entity_id, entity_type, action, new_values, user_id, created_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440070', '550e8400-e29b-41d4-a716-446655440010', 'RFQ', 'CREATE', '{"rfq_id": "550e8400-e29b-41d4-a716-446655440010"}', '550e8400-e29b-41d4-a716-446655440003', NOW());

INSERT INTO system_notifications (id, user_id, notification_type, title, message, is_read, created_at)
VALUES
    ('550e8400-e29b-41d4-a716-446655440080', '550e8400-e29b-41d4-a716-446655440001', 'INFO', 'نمونه اعلان', 'این یک اعلان نمونه برای تست است.', false, NOW());

COMMIT;
