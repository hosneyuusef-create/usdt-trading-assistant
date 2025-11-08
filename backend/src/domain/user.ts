import { randomUUID } from "node:crypto";
import bcrypt from "bcryptjs";
import { db } from "../database/client.js";
import {
  createDualControlRequest,
  resolveDualControlRequest,
} from "./dual-control.js";
import { recordAuditLog } from "../utils/audit.js";
import { DomainError } from "../utils/errors.js";

export type UserRole = "admin" | "ops" | "viewer" | "system";
export type UserStatus = "pending" | "approved" | "rejected" | "disabled";

export type User = {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  status: UserStatus;
  telegramHandle?: string | null;
  phoneNumber?: string | null;
  metadata: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
};

type UserRow = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  status: UserStatus;
  telegram_handle?: string | null;
  phone_number?: string | null;
  metadata: Record<string, unknown>;
  hashed_password?: string;
  created_at: Date;
  updated_at: Date;
};

export type CreateUserInput = {
  email: string;
  firstName: string;
  lastName: string;
  password: string;
  role?: UserRole;
  createdBy?: string;
};

const SALT_ROUNDS = 12;

export const createUser = async (input: CreateUserInput) => {
  const existing = await db("users").where({ email: input.email }).first();
  if (existing) {
    throw new DomainError("User already exists", 409);
  }

  const hashedPassword = await bcrypt.hash(input.password, SALT_ROUNDS);
  const insertedId = randomUUID();
  const [userRow] = await db("users")
    .insert({
      id: insertedId,
      email: input.email,
      first_name: input.firstName,
      last_name: input.lastName,
      role: input.role ?? "viewer",
      status: "pending",
      hashed_password: hashedPassword,
      metadata: {},
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");

  await createDualControlRequest({
    entityType: "user",
    entityId: insertedId,
    action: "user_activation",
    requestedBy: input.createdBy ?? insertedId,
    context: { email: input.email },
  });

  await recordAuditLog({
    actorUserId: input.createdBy ?? insertedId,
    action: "user_created",
    entityType: "user",
    entityId: insertedId,
    metadata: { role: input.role ?? "viewer" },
  });

  return mapRow(userRow);
};

export const listUsersByStatus = async (
  status: UserStatus,
): Promise<User[]> => {
  const rows = await db("users").where({ status }).select("*");
  return rows.map(mapRow);
};

export const getUserById = async (id: string): Promise<User | null> => {
  const row = await db("users").where({ id }).first();
  return row ? mapRow(row) : null;
};

export type ApproveUserInput = {
  userId: string;
  approverId: string;
  dualControlRequestId: string;
  approvalReason: string;
  secondaryApproverId: string;
};

export const approveUser = async ({
  userId,
  approverId,
  dualControlRequestId,
  approvalReason,
  secondaryApproverId,
}: ApproveUserInput) => {
  const user = await getUserById(userId);
  if (!user) {
    throw new DomainError("User not found", 404);
  }
  if (user.status !== "pending") {
    throw new DomainError("User already processed", 409);
  }

  await resolveDualControlRequest({
    requestId: dualControlRequestId,
    approverId,
    approvalReason,
    secondaryApproverId,
    approve: true,
  });

  const [updated] = await db("users")
    .where({ id: userId })
    .update(
      {
        status: "approved",
        updated_at: new Date(),
      },
      "*",
    );

  await recordAuditLog({
    actorUserId: approverId,
    action: "user_approved",
    entityType: "user",
    entityId: userId,
    metadata: {
      reason: approvalReason,
      secondaryApproverId,
    },
  });

  return mapRow(updated);
};

export type RejectUserInput = {
  userId: string;
  approverId: string;
  dualControlRequestId: string;
  reason: string;
};

export const rejectUser = async ({
  userId,
  approverId,
  dualControlRequestId,
  reason,
}: RejectUserInput) => {
  if (!reason || !reason.trim()) {
    throw new DomainError("Rejection reason is required", 400);
  }
  const user = await getUserById(userId);
  if (!user) {
    throw new DomainError("User not found", 404);
  }
  if (user.status !== "pending") {
    throw new DomainError("User already processed", 409);
  }

  await resolveDualControlRequest({
    requestId: dualControlRequestId,
    approverId,
    approve: false,
    rejectionReason: reason,
  });

  const [updated] = await db("users")
    .where({ id: userId })
    .update(
      {
        status: "rejected",
        updated_at: new Date(),
      },
      "*",
    );

  await recordAuditLog({
    actorUserId: approverId,
    action: "user_rejected",
    entityType: "user",
    entityId: userId,
    metadata: { reason },
  });

  return mapRow(updated);
};

export const verifyPassword = async (
  email: string,
  plaintext: string,
): Promise<User | null> => {
  const row = await db("users").where({ email }).first();
  if (!row) {
    return null;
  }
  const matches = await bcrypt.compare(plaintext, row.hashed_password);
  if (!matches) {
    return null;
  }
  return mapRow(row);
};

const mapRow = (row: UserRow): User => ({
  id: row.id,
  email: row.email,
  firstName: row.first_name,
  lastName: row.last_name,
  role: row.role,
  status: row.status,
  telegramHandle: row.telegram_handle,
  phoneNumber: row.phone_number,
  metadata: row.metadata ?? {},
  createdAt: row.created_at,
  updatedAt: row.updated_at,
});
