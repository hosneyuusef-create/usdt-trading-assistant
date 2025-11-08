import { db } from "../src/database/client.js";
import { createUser, approveUser } from "../src/domain/user.js";
import bcrypt from "bcryptjs";

const run = async () => {
  const now = new Date();
  const passwordHash = await bcrypt.hash("OpsPassword123!", 12);
  const existingSmoke = await db("users")
    .where({ email: "smoke-user@example.com" })
    .first();
  if (existingSmoke) {
    await db("dual_control_requests").where({ entity_id: existingSmoke.id }).del();
    await db("users").where({ id: existingSmoke.id }).del();
  }

  const [approver] = await db("users")
    .insert({
      email: "approver@example.com",
      first_name: "Ops",
      last_name: "Lead",
      role: "admin",
      status: "approved",
      hashed_password: passwordHash,
      metadata: {},
      created_at: now,
      updated_at: now,
    })
    .onConflict("email")
    .merge({
      status: "approved",
      hashed_password: passwordHash,
      updated_at: now,
    })
    .returning("*");

  const [secondary] = await db("users")
    .insert({
      email: "secondary@example.com",
      first_name: "Ops",
      last_name: "Secondary",
      role: "ops",
      status: "approved",
      hashed_password: passwordHash,
      metadata: {},
      created_at: now,
      updated_at: now,
    })
    .onConflict("email")
    .merge({
      status: "approved",
      hashed_password: passwordHash,
      updated_at: now,
    })
    .returning("*");

  const user = await createUser({
    email: "smoke-user@example.com",
    firstName: "Smoke",
    lastName: "Test",
    password: "ChangeMe123!",
    role: "ops",
    createdBy: approver.id,
  });

  const dualControl = await db("dual_control_requests")
    .where({ entity_id: user.id })
    .first();

  await approveUser({
    userId: user.id,
    dualControlRequestId: dualControl.id,
    approverId: approver.id,
    approvalReason: "Smoke test approval",
    secondaryApproverId: secondary.id,
  });

  const approved = await db("users").where({ id: user.id }).first();
  console.log("Manual smoke completed:", {
    userId: approved.id,
    status: approved.status,
    email: approved.email,
  });

  await db.destroy();
};

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
