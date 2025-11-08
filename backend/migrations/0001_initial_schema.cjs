const withUuidDefault = (table, knex) =>
  table.uuid("id").primary().defaultTo(knex.raw("gen_random_uuid()"));

async function up(knex) {
  await knex.raw('CREATE EXTENSION IF NOT EXISTS "pgcrypto";');
  await knex.raw('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";');

  await knex.schema.createTable("users", (table) => {
    withUuidDefault(table, knex);
    table.string("email").notNullable().unique();
    table.string("first_name").notNullable();
    table.string("last_name").notNullable();
    table
      .enu("role", ["admin", "ops", "viewer", "system"], {
        useNative: true,
        enumName: "user_role",
      })
      .notNullable()
      .defaultTo("viewer");
    table
      .enu("status", ["pending", "approved", "rejected", "disabled"], {
        useNative: true,
        enumName: "user_status",
      })
      .notNullable()
      .defaultTo("pending");
    table.string("hashed_password").notNullable();
    table.string("mfa_secret");
    table.string("telegram_handle");
    table.string("phone_number");
    table.timestamp("last_login_at");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("dual_control_requests", (table) => {
    withUuidDefault(table, knex);
    table
      .enu("status", ["pending", "approved", "rejected"], {
        useNative: true,
        enumName: "dual_control_status",
      })
      .notNullable()
      .defaultTo("pending");
    table.string("entity_type").notNullable();
    table.uuid("entity_id").notNullable();
    table.string("action").notNullable();
    table
      .uuid("requested_by")
      .notNullable()
      .references("id")
      .inTable("users")
      .onDelete("CASCADE");
    table
      .uuid("primary_approver_id")
      .references("id")
      .inTable("users")
      .onDelete("SET NULL");
    table.timestamp("approved_at");
    table.timestamp("rejected_at");
    table.text("rejection_reason");
    table.jsonb("context").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("liquidity_providers", (table) => {
    withUuidDefault(table, knex);
    table.string("name").notNullable().unique();
    table
      .enu("status", ["active", "paused", "disabled"], {
        useNative: true,
        enumName: "lp_status",
      })
      .notNullable()
      .defaultTo("active");
    table.string("endpoint_url");
    table.integer("max_quote_notional");
    table.integer("last_latency_ms");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("rfqs", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("user_id")
      .notNullable()
      .references("id")
      .inTable("users")
      .onDelete("CASCADE");
    table.string("asset").notNullable();
    table.decimal("notional", 32, 8).notNullable();
    table
      .enu("side", ["buy", "sell"], {
        useNative: true,
        enumName: "rfq_side",
      })
      .notNullable();
    table
      .enu("status", ["draft", "quoted", "accepted", "expired", "cancelled"], {
        useNative: true,
        enumName: "rfq_status",
      })
      .notNullable()
      .defaultTo("draft");
    table.timestamp("expires_at").notNullable();
    table.timestamp("accepted_at");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("quotes", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("rfq_id")
      .notNullable()
      .references("id")
      .inTable("rfqs")
      .onDelete("CASCADE");
    table
      .uuid("liquidity_provider_id")
      .references("id")
      .inTable("liquidity_providers")
      .onDelete("SET NULL");
    table.decimal("price", 32, 8).notNullable();
    table.decimal("spread_bps", 10, 4).notNullable();
    table
      .enu("status", ["pending", "sent", "expired", "accepted", "rejected"], {
        useNative: true,
        enumName: "quote_status",
      })
      .notNullable()
      .defaultTo("pending");
    table.timestamp("valid_until").notNullable();
    table.timestamps(true, true);
  });

  await knex.schema.createTable("fills", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("quote_id")
      .notNullable()
      .references("id")
      .inTable("quotes")
      .onDelete("CASCADE");
    table.decimal("fill_amount", 32, 8).notNullable();
    table.string("tx_hash");
    table
      .enu("status", ["pending", "confirmed", "failed"], {
        useNative: true,
        enumName: "fill_status",
      })
      .notNullable()
      .defaultTo("pending");
    table.timestamp("filled_at");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("settlements", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("fill_id")
      .notNullable()
      .references("id")
      .inTable("fills")
      .onDelete("CASCADE");
    table
      .enu("status", ["queued", "processing", "settled", "failed"], {
        useNative: true,
        enumName: "settlement_status",
      })
      .notNullable()
      .defaultTo("queued");
    table.string("network");
    table.string("destination_address");
    table.string("tx_hash");
    table.integer("retry_count").notNullable().defaultTo(0);
    table.text("failure_reason");
    table.timestamp("settled_at");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("settlement_jobs", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("settlement_id")
      .references("id")
      .inTable("settlements")
      .onDelete("CASCADE");
    table
      .enu("status", ["queued", "in_progress", "succeeded", "failed"], {
        useNative: true,
        enumName: "settlement_job_status",
      })
      .notNullable()
      .defaultTo("queued");
    table.jsonb("payload").notNullable().defaultTo("{}");
    table.integer("attempts").notNullable().defaultTo(0);
    table.timestamp("next_run_at");
    table.string("error_message");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("wallets", (table) => {
    withUuidDefault(table, knex);
    table.string("label").notNullable();
    table.string("address").notNullable().unique();
    table.string("network").notNullable();
    table.decimal("balance", 32, 8).notNullable().defaultTo(0);
    table
      .enu("status", ["active", "suspended", "retired"], {
        useNative: true,
        enumName: "wallet_status",
      })
      .notNullable()
      .defaultTo("active");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("wallet_transactions", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("wallet_id")
      .notNullable()
      .references("id")
      .inTable("wallets")
      .onDelete("CASCADE");
    table
      .uuid("settlement_id")
      .references("id")
      .inTable("settlements")
      .onDelete("SET NULL");
    table
      .enu("direction", ["credit", "debit"], {
        useNative: true,
        enumName: "wallet_direction",
      })
      .notNullable();
    table.decimal("amount", 32, 8).notNullable();
    table.string("currency").notNullable().defaultTo("USDT");
    table.string("tx_hash");
    table
      .enu("status", ["pending", "confirmed", "failed"], {
        useNative: true,
        enumName: "wallet_tx_status",
      })
      .notNullable()
      .defaultTo("pending");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("api_keys", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("user_id")
      .notNullable()
      .references("id")
      .inTable("users")
      .onDelete("CASCADE");
    table.string("name").notNullable();
    table.string("hashed_secret").notNullable();
    table.jsonb("scopes").notNullable().defaultTo("[]");
    table.timestamp("last_used_at");
    table.boolean("is_active").notNullable().defaultTo(true);
    table.timestamps(true, true);
  });

  await knex.schema.createTable("mfa_factors", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("user_id")
      .notNullable()
      .references("id")
      .inTable("users")
      .onDelete("CASCADE");
    table
      .enu("method", ["totp", "sms", "email"], {
        useNative: true,
        enumName: "mfa_method",
      })
      .notNullable()
      .defaultTo("totp");
    table.string("secret").notNullable();
    table.timestamp("verified_at");
    table.timestamp("revoked_at");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("notifications", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("user_id")
      .references("id")
      .inTable("users")
      .onDelete("SET NULL");
    table
      .enu("channel", ["email", "sms", "telegram", "webhook"], {
        useNative: true,
        enumName: "notification_channel",
      })
      .notNullable();
    table.string("template_name").notNullable();
    table.jsonb("payload").notNullable().defaultTo("{}");
    table
      .enu("status", ["queued", "sent", "failed"], {
        useNative: true,
        enumName: "notification_status",
      })
      .notNullable()
      .defaultTo("queued");
    table.string("error_message");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("csrf_tokens", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("user_id")
      .references("id")
      .inTable("users")
      .onDelete("CASCADE");
    table.string("token").notNullable().unique();
    table.timestamp("expires_at").notNullable();
    table.timestamp("consumed_at");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("feature_flags", (table) => {
    table.string("key").primary();
    table.boolean("is_enabled").notNullable().defaultTo(false);
    table.string("description");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("sla_policies", (table) => {
    withUuidDefault(table, knex);
    table.string("name").notNullable().unique();
    table.text("description").notNullable();
    table.integer("target_ms").notNullable();
    table.integer("breach_threshold_ms").notNullable();
    table.boolean("is_active").notNullable().defaultTo(true);
    table.timestamps(true, true);
  });

  await knex.schema.createTable("spread_configs", (table) => {
    withUuidDefault(table, knex);
    table.string("asset_pair").notNullable().unique();
    table.decimal("base_spread_bps", 10, 4).notNullable();
    table.decimal("max_spread_bps", 10, 4).notNullable();
    table.boolean("auto_reprice").notNullable().defaultTo(true);
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("alert_rules", (table) => {
    withUuidDefault(table, knex);
    table.string("name").notNullable().unique();
    table.string("metric_key").notNullable();
    table.decimal("threshold", 20, 4).notNullable();
    table.integer("window_seconds").notNullable().defaultTo(60);
    table
      .enu("severity", ["info", "warning", "critical"], {
        useNative: true,
        enumName: "alert_severity",
      })
      .notNullable()
      .defaultTo("warning");
    table.integer("debounce_seconds").notNullable().defaultTo(60);
    table.string("owner_email").notNullable();
    table.boolean("is_active").notNullable().defaultTo(true);
    table.timestamps(true, true);
  });

  await knex.schema.createTable("alert_events", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("rule_id")
      .notNullable()
      .references("id")
      .inTable("alert_rules")
      .onDelete("CASCADE");
    table
      .enu("status", ["triggered", "acknowledged", "resolved"], {
        useNative: true,
        enumName: "alert_event_status",
      })
      .notNullable()
      .defaultTo("triggered");
    table.jsonb("details").notNullable().defaultTo("{}");
    table.timestamp("triggered_at").notNullable().defaultTo(knex.fn.now());
    table.timestamp("resolved_at");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("audit_logs", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("actor_user_id")
      .references("id")
      .inTable("users")
      .onDelete("SET NULL");
    table.string("action").notNullable();
    table.string("entity_type").notNullable();
    table.uuid("entity_id");
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  await knex.schema.createTable("api_sessions", (table) => {
    withUuidDefault(table, knex);
    table
      .uuid("user_id")
      .notNullable()
      .references("id")
      .inTable("users")
      .onDelete("CASCADE");
    table.string("refresh_token").notNullable().unique();
    table.timestamp("expires_at").notNullable();
    table.boolean("revoked").notNullable().defaultTo(false);
    table.timestamps(true, true);
  });

  await knex.schema.createTable("metrics_snapshots", (table) => {
    withUuidDefault(table, knex);
    table.string("metric_key").notNullable();
    table.decimal("value", 20, 4).notNullable();
    table.timestamp("captured_at").notNullable().defaultTo(knex.fn.now());
    table.jsonb("labels").notNullable().defaultTo("{}");
  });

  await knex.schema.createTable("telegram_sessions", (table) => {
    withUuidDefault(table, knex);
    table.string("chat_id").notNullable();
    table
      .uuid("user_id")
      .references("id")
      .inTable("users")
      .onDelete("SET NULL");
    table.jsonb("state").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });
}

async function down(knex) {
  await knex.schema
    .dropTableIfExists("telegram_sessions")
    .dropTableIfExists("metrics_snapshots")
    .dropTableIfExists("api_sessions")
    .dropTableIfExists("audit_logs")
    .dropTableIfExists("alert_events")
    .dropTableIfExists("alert_rules")
    .dropTableIfExists("spread_configs")
    .dropTableIfExists("sla_policies")
    .dropTableIfExists("feature_flags")
    .dropTableIfExists("csrf_tokens")
    .dropTableIfExists("notifications")
    .dropTableIfExists("mfa_factors")
    .dropTableIfExists("api_keys")
    .dropTableIfExists("wallet_transactions")
    .dropTableIfExists("wallets")
    .dropTableIfExists("settlement_jobs")
    .dropTableIfExists("settlements")
    .dropTableIfExists("fills")
    .dropTableIfExists("quotes")
    .dropTableIfExists("rfqs")
    .dropTableIfExists("liquidity_providers")
    .dropTableIfExists("dual_control_requests")
    .dropTableIfExists("users");

  await knex.raw('DROP TYPE IF EXISTS alert_event_status;');
  await knex.raw('DROP TYPE IF EXISTS alert_severity;');
  await knex.raw('DROP TYPE IF EXISTS notification_status;');
  await knex.raw('DROP TYPE IF EXISTS notification_channel;');
  await knex.raw('DROP TYPE IF EXISTS mfa_method;');
  await knex.raw('DROP TYPE IF EXISTS wallet_tx_status;');
  await knex.raw('DROP TYPE IF EXISTS wallet_direction;');
  await knex.raw('DROP TYPE IF EXISTS wallet_status;');
  await knex.raw('DROP TYPE IF EXISTS settlement_job_status;');
  await knex.raw('DROP TYPE IF EXISTS settlement_status;');
  await knex.raw('DROP TYPE IF EXISTS fill_status;');
  await knex.raw('DROP TYPE IF EXISTS quote_status;');
  await knex.raw('DROP TYPE IF EXISTS rfq_status;');
  await knex.raw('DROP TYPE IF EXISTS rfq_side;');
  await knex.raw('DROP TYPE IF EXISTS lp_status;');
  await knex.raw('DROP TYPE IF EXISTS dual_control_status;');
  await knex.raw('DROP TYPE IF EXISTS user_status;');
  await knex.raw('DROP TYPE IF EXISTS user_role;');
}

module.exports = { up, down };
