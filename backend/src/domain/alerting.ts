import { randomUUID } from "node:crypto";
import { env } from "../config/env.js";
import { db } from "../database/client.js";
import { alertRateCounter, alertThrottleCounter } from "./metrics.js";

export type AlertSeverity = "info" | "warning" | "critical";

type RawAlertRuleRow = {
  id: string;
  name: string;
  metric_key: string;
  threshold: number | string;
  window_seconds: number;
  severity: AlertSeverity;
  debounce_seconds: number;
  owner_email: string;
  is_active: boolean;
};

type AlertRuleRecord = {
  id: string;
  name: string;
  metric_key: string;
  threshold: number;
  window_seconds: number;
  severity: AlertSeverity;
  debounce_seconds: number;
  owner_email: string;
  is_active: boolean;
};

export type AlertPayload = {
  ruleId: string;
  details?: Record<string, unknown>;
  severity: AlertSeverity;
};

export type EnsureAlertRuleInput = {
  name: string;
  metricKey: string;
  threshold: number;
  severity: AlertSeverity;
  ownerEmail?: string;
  windowSeconds?: number;
  debounceSeconds?: number;
};

const ruleCacheById = new Map<string, AlertRuleRecord>();
const ruleCacheByName = new Map<string, AlertRuleRecord>();

const normalizeRule = (row: RawAlertRuleRow): AlertRuleRecord => ({
  id: row.id,
  name: row.name,
  metric_key: row.metric_key,
  threshold: Number(row.threshold),
  window_seconds: row.window_seconds,
  severity: row.severity,
  debounce_seconds: row.debounce_seconds,
  owner_email: row.owner_email,
  is_active: row.is_active,
});

const cacheRule = (rule: AlertRuleRecord) => {
  ruleCacheById.set(rule.id, rule);
  ruleCacheByName.set(rule.name, rule);
  return rule;
};

const getRuleById = async (ruleId: string): Promise<AlertRuleRecord | null> => {
  const cached = ruleCacheById.get(ruleId);
  if (cached) {
    return cached;
  }
  const row = await db("alert_rules").where({ id: ruleId }).first();
  return row ? cacheRule(normalizeRule(row)) : null;
};

export const ensureAlertRule = async (
  input: EnsureAlertRuleInput,
): Promise<AlertRuleRecord> => {
  const ownerEmail = input.ownerEmail ?? env.ALERT_OWNER_EMAIL;
  const debounceSeconds = input.debounceSeconds ?? env.ALERT_DEBOUNCE_SECONDS;
  const windowSeconds = input.windowSeconds ?? 60;
  const existing = ruleCacheByName.get(input.name)
    ?? (await db("alert_rules").where({ name: input.name }).first());

  if (!existing) {
    const [inserted] = await db("alert_rules")
      .insert({
        id: randomUUID(),
        name: input.name,
        metric_key: input.metricKey,
        threshold: input.threshold,
        window_seconds: windowSeconds,
        severity: input.severity,
        debounce_seconds: debounceSeconds,
        owner_email: ownerEmail,
        is_active: true,
        created_at: new Date(),
        updated_at: new Date(),
      })
      .returning("*");
    return cacheRule(normalizeRule(inserted));
  }

  const normalized = normalizeRule(existing);
  const needsUpdate =
    normalized.metric_key !== input.metricKey ||
    normalized.threshold !== input.threshold ||
    normalized.window_seconds !== windowSeconds ||
    normalized.debounce_seconds !== debounceSeconds ||
    normalized.owner_email !== ownerEmail ||
    normalized.severity !== input.severity;

  if (needsUpdate) {
    const [updated] = await db("alert_rules")
      .where({ id: normalized.id })
      .update(
        {
          metric_key: input.metricKey,
          threshold: input.threshold,
          window_seconds: windowSeconds,
          severity: input.severity,
          debounce_seconds: debounceSeconds,
          owner_email: ownerEmail,
          updated_at: new Date(),
        },
        "*",
      );
    return cacheRule(normalizeRule(updated));
  }

  return cacheRule(normalized);
};

export const emitAlert = async (payload: AlertPayload) => {
  const rule = await getRuleById(payload.ruleId);
  if (!rule || !rule.is_active) {
    return;
  }

  const cutoff = new Date(Date.now() - rule.debounce_seconds * 1000);
  const recent = await db("alert_events")
    .where({ rule_id: payload.ruleId })
    .andWhere("created_at", ">", cutoff)
    .first();
  if (recent) {
    alertThrottleCounter.inc({ rule_id: payload.ruleId });
    return;
  }

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

const QUEUE_ALERT_NAME = "settlement_queue_backlog";
const FLAGGED_ALERT_NAME = "settlement_flagged_spike";

export const maybeEmitQueueAlert = async (queueSize: number) => {
  if (queueSize < env.ALERT_QUEUE_THRESHOLD) {
    return;
  }
  const rule = await ensureAlertRule({
    name: QUEUE_ALERT_NAME,
    metricKey: "settlement_queue_size",
    threshold: env.ALERT_QUEUE_THRESHOLD,
    severity: "warning",
  });
  await emitAlert({
    ruleId: rule.id,
    severity: "warning",
    details: {
      queueSize,
      threshold: env.ALERT_QUEUE_THRESHOLD,
    },
  });
};

export const maybeEmitFlaggedAlert = async () => {
  const since = new Date(Date.now() - env.ALERT_DEBOUNCE_SECONDS * 1000);
  const result =
    (await db("settlement_flagged_events")
      .where("created_at", ">", since)
      .count<{ count: string }>("id as count")
      .first()) ?? { count: "0" };
  const flagged = Number(result.count);
  if (flagged < env.ALERT_FLAGGED_THRESHOLD) {
    return;
  }

  const rule = await ensureAlertRule({
    name: FLAGGED_ALERT_NAME,
    metricKey: "settlement_flagged_total",
    threshold: env.ALERT_FLAGGED_THRESHOLD,
    severity: "warning",
  });
  await emitAlert({
    ruleId: rule.id,
    severity: "warning",
    details: {
      flaggedLastWindow: flagged,
      threshold: env.ALERT_FLAGGED_THRESHOLD,
      windowSeconds: env.ALERT_DEBOUNCE_SECONDS,
    },
  });
};

const errorHistory = new Map<string, number[]>();
const BACKEND_ERROR_RULE_PREFIX = "backend_error_rate";

export const recordBackendError = async (
  moduleName: string,
  extraDetails?: Record<string, unknown>,
) => {
  const now = Date.now();
  const windowMs = env.ALERT_DEBOUNCE_SECONDS * 1000;
  const history = errorHistory.get(moduleName) ?? [];
  history.push(now);
  while (history.length && now - history[0] > windowMs) {
    history.shift();
  }
  errorHistory.set(moduleName, history);

  if (history.length < env.ALERT_ERROR_THRESHOLD) {
    return;
  }

  const rule = await ensureAlertRule({
    name: `${BACKEND_ERROR_RULE_PREFIX}_${moduleName}`,
    metricKey: "backend_error_gauge",
    threshold: env.ALERT_ERROR_THRESHOLD,
    severity: "warning",
  });
  await emitAlert({
    ruleId: rule.id,
    severity: "warning",
    details: {
      module: moduleName,
      recentErrors: history.length,
      threshold: env.ALERT_ERROR_THRESHOLD,
      ...extraDetails,
    },
  });
  history.length = 0;
};
