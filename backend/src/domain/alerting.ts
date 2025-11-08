import { randomUUID } from "node:crypto";
import { db } from "../database/client.js";
import { alertRateCounter } from "./metrics.js";

export type AlertSeverity = "info" | "warning" | "critical";

export type AlertPayload = {
  ruleId: string;
  details?: Record<string, unknown>;
  severity: AlertSeverity;
};

export const emitAlert = async (payload: AlertPayload) => {
  await db("alert_events").insert({
    id: randomUUID(),
    rule_id: payload.ruleId,
    status: "triggered",
    details: payload.details ?? {},
    created_at: new Date(),
    updated_at: new Date(),
  });
  alertRateCounter.inc({ severity: payload.severity });
};
