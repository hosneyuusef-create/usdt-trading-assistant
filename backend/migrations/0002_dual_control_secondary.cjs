async function up(knex) {
  await knex.schema.alterTable("dual_control_requests", (table) => {
    table.text("approval_reason");
    table
      .uuid("secondary_approver_id")
      .references("id")
      .inTable("users")
      .onDelete("SET NULL");
    table.timestamp("secondary_approved_at");
  });

  await knex("dual_control_requests")
    .update({
      approval_reason: knex.raw(
        "COALESCE(approval_reason, 'legacy-approval-migration')",
      ),
      secondary_approver_id: knex.raw(
        "COALESCE(secondary_approver_id, primary_approver_id)",
      ),
      secondary_approved_at: knex.raw(
        "COALESCE(secondary_approved_at, approved_at)",
      ),
    })
    .whereNotNull("approved_at");
}

async function down(knex) {
  await knex.schema.alterTable("dual_control_requests", (table) => {
    table.dropColumn("secondary_approved_at");
    table.dropColumn("secondary_approver_id");
    table.dropColumn("approval_reason");
  });
}

module.exports = { up, down };
