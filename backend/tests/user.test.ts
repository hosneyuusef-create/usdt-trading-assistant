import { randomUUID } from "node:crypto";
import bcrypt from "bcryptjs";
import { describe, expect, it } from "vitest";
import { db } from "../src/database/client.js";
import {
  createUser,
  listUsersByStatus,
  approveUser,
} from "../src/domain/user.js";

const insertApprovedUser = async (email: string, id = randomUUID()) => {
  const [row] = await db("users")
    .insert({
      id,
      email,
      first_name: "Ops",
      last_name: "User",
      role: "admin",
      status: "approved",
      hashed_password: await bcrypt.hash("Password123", 8),
      metadata: {},
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");
  return row;
};

describe("User domain", () => {
  it("creates a user and queues dual-control approval", async () => {
    const requester = await insertApprovedUser("requester@example.com");
  const user = await createUser({
    email: "pending@example.com",
    firstName: "Pending",
    lastName: "User",
    password: "Secret123!",
    role: "ops",
  });

    expect(user.status).toBe("pending");
    const pending = await listUsersByStatus("pending");
    expect(pending.length).toBe(1);

    const [dualControl] = await db("dual_control_requests")
      .where({ entity_id: user.id })
      .select();
    expect(dualControl).toBeDefined();
    expect(dualControl.status).toBe("pending");
  });

  it("approves a user through dual-control", async () => {
    const approver = await insertApprovedUser("approver@example.com");
    const secondary = await insertApprovedUser("secondary@example.com");
    const user = await createUser({
      email: "dual@example.com",
      firstName: "Dual",
      lastName: "Candidate",
      password: "Secret123!",
      role: "viewer",
    });
    const dualControl = await db("dual_control_requests")
      .where({ entity_id: user.id })
      .first();

    await approveUser({
      userId: user.id,
      approverId: approver.id,
      dualControlRequestId: dualControl.id,
      approvalReason: "Need ops coverage",
      secondaryApproverId: secondary.id,
    });

    const refreshed = await db("users").where({ id: user.id }).first();
    expect(refreshed.status).toBe("approved");
  });

  it("ensures approval reason and distinct secondary approver", async () => {
    const approver = await insertApprovedUser("approver2@example.com");
    const user = await createUser({
      email: "dual-missing-reason@example.com",
      firstName: "Dual",
      lastName: "Candidate2",
      password: "Secret123!",
      role: "viewer",
    });
    const dualControl = await db("dual_control_requests")
      .where({ entity_id: user.id })
      .first();

    await expect(
      approveUser({
        userId: user.id,
        approverId: approver.id,
        dualControlRequestId: dualControl.id,
        approvalReason: "",
        secondaryApproverId: approver.id,
      }),
    ).rejects.toThrow();
  });
});
