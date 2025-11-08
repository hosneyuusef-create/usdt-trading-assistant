const { randomUUID } = require("node:crypto");

async function up(knex) {
  await knex.schema.createTable("settlement_flagged_events", (table) => {
    table
      .uuid("id")
      .primary()
      .defaultTo(knex.raw("gen_random_uuid()"));
    table.uuid("rfq_id");
    table.uuid("quote_id");
    table.uuid("fill_id");
    table
      .uuid("settlement_id")
      .references("id")
      .inTable("settlements")
      .onDelete("SET NULL");
    table.string("reason").notNullable();
    table.boolean("auto_settlement_enabled").notNullable().defaultTo(false);
    table.jsonb("metadata").notNullable().defaultTo("{}");
    table.timestamps(true, true);
  });

  const now = new Date();
  await knex("alert_rules")
    .insert({
      id: randomUUID(),
      name: "auto_settlement_disabled",
      metric_key: "auto_settlement_status",
      threshold: 0,
      window_seconds: 60,
      severity: "warning",
      debounce_seconds: 60,
      owner_email: "ops@example.com",
      is_active: true,
      created_at: now,
      updated_at: now,
    })
    .onConflict("name")
    .ignore();
}

async function down(knex) {
  await knex.schema.dropTableIfExists("settlement_flagged_events");
  await knex("alert_rules").where({ name: "auto_settlement_disabled" }).del();
}

module.exports = { up, down };
