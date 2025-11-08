import { randomUUID } from "node:crypto";
import { db } from "../database/client.js";
import { recordAuditLog } from "../utils/audit.js";
import { DomainError } from "../utils/errors.js";

export type DualControlStatus = "pending" | "approved" | "rejected";

export type DualControlRequest = {
  id: string;
  entityType: string;
  entityId: string;
  action: string;
  status: DualControlStatus;
  requestedBy: string;
  primaryApproverId?: string | null;
  approvalReason?: string | null;
  secondaryApproverId?: string | null;
  secondaryApprovedAt?: Date | null;
  approvedAt?: Date | null;
  rejectedAt?: Date | null;
  rejectionReason?: string | null;
  context?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
};

type DualControlRow = {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  status: DualControlStatus;
  requested_by: string;
  primary_approver_id?: string | null;
  approval_reason?: string | null;
  secondary_approver_id?: string | null;
  secondary_approved_at?: Date | null;
  approved_at?: Date | null;
  rejected_at?: Date | null;
  rejection_reason?: string | null;
  context?: Record<string, unknown>;
  created_at: Date;
  updated_at: Date;
};

export type CreateDualControlInput = {
  entityType: string;
  entityId: string;
  action: string;
  requestedBy: string;
  context?: Record<string, unknown>;
};

export const createDualControlRequest = async (
  input: CreateDualControlInput,
): Promise<DualControlRequest> => {
  const [record] = await db("dual_control_requests")
    .insert({
      id: randomUUID(),
      entity_type: input.entityType,
      entity_id: input.entityId,
      action: input.action,
      requested_by: input.requestedBy,
      context: input.context ?? {},
      status: "pending",
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");

  await recordAuditLog({
    actorUserId: input.requestedBy,
    action: "dual_control_requested",
    entityType: input.entityType,
    entityId: input.entityId,
    metadata: {
      action: input.action,
    },
  });

  return mapRow(record);
};

export type ResolveDualControlInput = {
  requestId: string;
  approverId: string;
  approvalReason?: string;
  secondaryApproverId?: string;
  approve: boolean;
  rejectionReason?: string;
};

export const resolveDualControlRequest = async ({
  requestId,
  approverId,
  approvalReason,
  secondaryApproverId,
  approve,
  rejectionReason,
}: ResolveDualControlInput): Promise<DualControlRequest> => {
  const existing = await db("dual_control_requests")
    .where({ id: requestId })
    .first();
  if (!existing) {
    throw new DomainError("Dual-control request not found", 404);
  }
  if (existing.status !== "pending") {
    throw new DomainError("Dual-control request already processed", 409);
  }

  if (approve) {
    if (!approvalReason || !approvalReason.trim()) {
      throw new DomainError("Approval reason is required", 400);
    }
    if (!secondaryApproverId) {
      throw new DomainError("Secondary approver is required", 400);
    }
    if (secondaryApproverId === approverId) {
      throw new DomainError("Secondary approver must differ from primary", 400);
    }
    const approvers = await db("users")
      .whereIn("id", [approverId, secondaryApproverId])
      .select("id");
    if (approvers.length !== 2) {
      throw new DomainError("Approver(s) not found", 404);
    }
  }

  const now = new Date();

  const patch = approve
    ? {
        status: "approved",
        primary_approver_id: approverId,
        approval_reason: approvalReason,
        secondary_approver_id: secondaryApproverId,
        secondary_approved_at: now,
        approved_at: now,
        updated_at: now,
      }
    : {
        status: "rejected",
        primary_approver_id: approverId,
        rejected_at: now,
        rejection_reason: rejectionReason ?? "not provided",
        updated_at: now,
      };

  const [updated] = await db("dual_control_requests")
    .where({ id: requestId })
    .update(patch)
    .returning("*");

  await recordAuditLog({
    actorUserId: approverId,
    action: approve ? "dual_control_approved" : "dual_control_rejected",
    entityType: existing.entity_type,
    entityId: existing.entity_id,
    metadata: {
      action: existing.action,
      rejectionReason: rejectionReason,
      secondaryApproverId: secondaryApproverId,
      approvalReason: approvalReason,
      secondaryApprovedAt: approve ? now : null,
    },
  });

  return mapRow(updated);
};

export const listPendingDualControlRequests = async (): Promise<
  DualControlRequest[]
> => {
  const rows = await db("dual_control_requests")
    .where({ status: "pending" })
    .orderBy("created_at", "asc");
  return rows.map(mapRow);
};

const mapRow = (row: DualControlRow): DualControlRequest => ({
  id: row.id,
  entityType: row.entity_type,
  entityId: row.entity_id,
  action: row.action,
  status: row.status,
  requestedBy: row.requested_by,
  primaryApproverId: row.primary_approver_id,
  approvalReason: row.approval_reason,
  secondaryApproverId: row.secondary_approver_id,
  secondaryApprovedAt: row.secondary_approved_at,
  approvedAt: row.approved_at,
  rejectedAt: row.rejected_at,
  rejectionReason: row.rejection_reason,
  context: row.context,
  createdAt: row.created_at,
  updatedAt: row.updated_at,
});
