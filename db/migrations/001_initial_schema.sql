-- database_schema_v1.sql
-- Stage: M05 | Date: 2025-10-23

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE customers (
    customer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    kyc_tier VARCHAR(16) NOT NULL,
    wallet_alias VARCHAR(128),
    email VARCHAR(256),
    status VARCHAR(16) DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE providers (
    provider_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    score NUMERIC(5,2) NOT NULL DEFAULT 0,
    collateral_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    max_capacity NUMERIC(18,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE admin_users (
    admin_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(256) UNIQUE NOT NULL,
    role VARCHAR(32) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE rfqs (
    rfq_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    rfq_type VARCHAR(8) NOT NULL,
    network VARCHAR(32) NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    min_fill NUMERIC(18,2),
    status VARCHAR(24) NOT NULL DEFAULT 'open',
    settlement_order VARCHAR(16) NOT NULL DEFAULT 'fiat_first',
    expiry_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE quotes (
    quote_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rfq_id UUID NOT NULL REFERENCES rfqs(rfq_id) ON DELETE CASCADE,
    provider_id UUID NOT NULL REFERENCES providers(provider_id) ON DELETE RESTRICT,
    unit_price NUMERIC(18,6) NOT NULL,
    capacity NUMERIC(18,2) NOT NULL,
    fee NUMERIC(18,4) DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'submitted',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE awards (
    award_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rfq_id UUID NOT NULL REFERENCES rfqs(rfq_id) ON DELETE CASCADE,
    quote_id UUID NOT NULL REFERENCES quotes(quote_id) ON DELETE CASCADE,
    selection_mode VARCHAR(16) NOT NULL,
    awarded_amount NUMERIC(18,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE settlements (
    settlement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    award_id UUID NOT NULL REFERENCES awards(award_id) ON DELETE CASCADE,
    status VARCHAR(24) NOT NULL DEFAULT 'pending',
    sla_deadline TIMESTAMPTZ,
    retry_count INT NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE settlement_legs (
    settlement_leg_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    settlement_id UUID NOT NULL REFERENCES settlements(settlement_id) ON DELETE CASCADE,
    quote_id UUID REFERENCES quotes(quote_id) ON DELETE SET NULL,
    leg_type VARCHAR(16) NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'pending',
    due_at TIMESTAMPTZ,
    tx_reference VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE disputes (
    dispute_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    settlement_id UUID NOT NULL REFERENCES settlements(settlement_id) ON DELETE CASCADE,
    claimant_customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    respondent_provider_id UUID NOT NULL REFERENCES providers(provider_id) ON DELETE RESTRICT,
    reason TEXT,
    status VARCHAR(24) NOT NULL DEFAULT 'open',
    decision TEXT,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    settlement_id UUID REFERENCES settlements(settlement_id) ON DELETE CASCADE,
    dispute_id UUID REFERENCES disputes(dispute_id) ON DELETE CASCADE,
    evidence_type VARCHAR(32) NOT NULL,
    storage_url TEXT,
    hash VARCHAR(256),
    metadata JSONB,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE dispute_actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispute_id UUID NOT NULL REFERENCES disputes(dispute_id) ON DELETE CASCADE,
    admin_id UUID REFERENCES admin_users(admin_id) ON DELETE SET NULL,
    actor_type VARCHAR(16) NOT NULL,
    notes TEXT,
    action_taken VARCHAR(32),
    action_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE notification_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel VARCHAR(16) NOT NULL,
    version INT NOT NULL,
    locale VARCHAR(8) NOT NULL DEFAULT 'fa-IR',
    body TEXT NOT NULL,
    metadata JSONB,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE notification_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES notification_templates(template_id) ON DELETE RESTRICT,
    related_type VARCHAR(32) NOT NULL,
    related_id UUID,
    status VARCHAR(16) NOT NULL DEFAULT 'queued',
    attempts INT NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE config_versions (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    json_payload JSONB NOT NULL,
    approved_by UUID REFERENCES admin_users(admin_id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

CREATE TABLE provider_score_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(provider_id) ON DELETE CASCADE,
    score NUMERIC(5,2) NOT NULL,
    collateral_balance NUMERIC(18,2) NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(64),
    updated_by VARCHAR(64)
);

-- Indexes
CREATE UNIQUE INDEX idx_customers_telegram_id ON customers(telegram_id);
CREATE INDEX idx_customers_kyc_tier_created_at ON customers(kyc_tier, created_at);
CREATE INDEX idx_customers_status ON customers(status);
CREATE INDEX idx_customers_created_at ON customers(created_at);

CREATE INDEX idx_providers_score_collateral ON providers(score, collateral_amount);
CREATE INDEX idx_providers_status ON providers(status);
CREATE INDEX idx_providers_created_at ON providers(created_at);

CREATE INDEX idx_admin_users_role ON admin_users(role);
CREATE INDEX idx_admin_users_last_login ON admin_users(last_login_at);

CREATE INDEX idx_rfqs_customer_status ON rfqs(customer_id, status);
CREATE INDEX idx_rfqs_type_network ON rfqs(rfq_type, network);
CREATE INDEX idx_rfqs_expiry_at ON rfqs(expiry_at);
CREATE INDEX idx_rfqs_settlement_order ON rfqs(settlement_order);
CREATE INDEX idx_rfqs_status_created ON rfqs(status, created_at);

CREATE INDEX idx_quotes_rfq ON quotes(rfq_id);
CREATE INDEX idx_quotes_provider ON quotes(provider_id);
CREATE INDEX idx_quotes_rfq_provider ON quotes(rfq_id, provider_id);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_status_created ON quotes(status, created_at DESC);

CREATE INDEX idx_awards_rfq ON awards(rfq_id);
CREATE INDEX idx_awards_quote ON awards(quote_id);
CREATE INDEX idx_awards_rfq_quote ON awards(rfq_id, quote_id);
CREATE INDEX idx_awards_created_at ON awards(created_at);

CREATE INDEX idx_settlements_award ON settlements(award_id);
CREATE INDEX idx_settlements_status ON settlements(status);
CREATE INDEX idx_settlements_award_status ON settlements(award_id, status);
CREATE INDEX idx_settlements_sla_deadline ON settlements(sla_deadline);

CREATE INDEX idx_settlement_legs_settlement ON settlement_legs(settlement_id);
CREATE INDEX idx_settlement_legs_quote ON settlement_legs(quote_id);
CREATE INDEX idx_settlement_legs_type_status ON settlement_legs(leg_type, status);

CREATE UNIQUE INDEX idx_evidence_hash ON evidence(hash);
CREATE INDEX idx_evidence_settlement ON evidence(settlement_id);
CREATE INDEX idx_evidence_dispute ON evidence(dispute_id);
CREATE INDEX idx_evidence_metadata_gin ON evidence USING GIN(metadata);

CREATE INDEX idx_disputes_settlement ON disputes(settlement_id);
CREATE INDEX idx_disputes_claimant ON disputes(claimant_customer_id);
CREATE INDEX idx_disputes_respondent ON disputes(respondent_provider_id);
CREATE INDEX idx_disputes_status_created ON disputes(status, opened_at);

CREATE INDEX idx_dispute_actions_dispute ON dispute_actions(dispute_id);
CREATE INDEX idx_dispute_actions_admin ON dispute_actions(admin_id);
CREATE INDEX idx_dispute_actions_action_at ON dispute_actions(action_at);

CREATE INDEX idx_notification_templates_channel_version ON notification_templates(channel, version);
CREATE INDEX idx_notification_templates_active ON notification_templates(active);

CREATE INDEX idx_notification_events_related ON notification_events(related_type, related_id);
CREATE INDEX idx_notification_events_status_attempts ON notification_events(status, attempts);
CREATE INDEX idx_notification_events_created_at ON notification_events(created_at);

CREATE INDEX idx_config_versions_applied_at ON config_versions(applied_at DESC);
CREATE INDEX idx_config_versions_payload_gin ON config_versions USING GIN(json_payload);

CREATE INDEX idx_provider_score_snapshots_provider_time ON provider_score_snapshots(provider_id, captured_at);
CREATE INDEX idx_provider_score_snapshots_score ON provider_score_snapshots(score);

-- End schema

