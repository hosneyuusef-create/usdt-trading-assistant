import { db } from "../database/client.js";
import { logger } from "./logger.js";

export type AuditLogEntry = {
  actorUserId?: string | null;
  action: string;
  entityType: string;
  entityId?: string | null;
  metadata?: Record<string, unknown>;
};

export const recordAuditLog = async (entry: AuditLogEntry) => {
  try {
    await db("audit_logs").insert({
      actor_user_id: entry.actorUserId ?? null,
      action: entry.action,
      entity_type: entry.entityType,
      entity_id: entry.entityId ?? null,
      metadata: entry.metadata ?? {},
      created_at: new Date(),
      updated_at: new Date(),
    });
  } catch (error) {
    logger.error(
      {
        err: error,
        entry,
      },
      "Failed to persist audit log",
    );
  }
};
