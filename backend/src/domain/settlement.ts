import { randomUUID } from "node:crypto";
import { db } from "../database/client.js";
import { DomainError } from "../utils/errors.js";
import { logger } from "../utils/logger.js";
import { isAutoSettlementEnabled } from "./feature-flags.js";
import { emitAlert } from "./alerting.js";
import {
  autoSettlementStatusGauge,
  flaggedOffGauge,
  settlementFlaggedCounter,
  settlementQueueGauge,
} from "./metrics.js";
import { ensureWallet, recordWalletMovement } from "./wallet.js";

export type SettlementJob = {
  id: string;
  settlementId: string | null;
  status: "queued" | "in_progress" | "succeeded" | "failed";
  payload: Record<string, unknown>;
  attempts: number;
  errorMessage?: string | null;
  createdAt: Date;
  updatedAt: Date;
};

type SettlementJobRow = {
  id: string;
  settlement_id: string | null;
  status: SettlementJob["status"];
  payload: Record<string, unknown>;
  attempts: number;
  error_message?: string | null;
  created_at: Date;
  updated_at: Date;
};

type SettlementWorkItem = {
  rfqId: string;
  quoteId: string;
  fillId: string;
  notional: number;
};

type SettlementResult = "flagged" | "queued";

const AUTO_SETTLEMENT_ALERT_NAME = "auto_settlement_disabled";

export const getNextSettlementJob = async (): Promise<SettlementJob | null> => {
  const row = await db("settlement_jobs")
    .where({ status: "queued" })
    .orderBy("created_at", "asc")
    .first();
  return row ? mapJob(row) : null;
};

export const markJobInProgress = async (jobId: string) => {
  const updated = await db("settlement_jobs")
    .where({ id: jobId, status: "queued" })
    .update(
      {
        status: "in_progress",
        updated_at: new Date(),
        attempts: db.raw("attempts + 1"),
      },
      "*",
    );
  if (!updated.length) {
    throw new DomainError("Settlement job no longer available", 409);
  }
  await refreshQueueGauge();
  return mapJob(updated[0]);
};

export type CompleteJobInput = {
  jobId: string;
  walletAddress: string;
  walletNetwork: string;
  amount: number;
  txHash?: string;
};

export const markJobSucceeded = async (input: CompleteJobInput) => {
  const job = await db("settlement_jobs").where({ id: input.jobId }).first();
  if (!job) throw new DomainError("Job not found", 404);

  const wallet = await ensureWallet({
    label: `${input.walletNetwork} settlement`,
    address: input.walletAddress,
    network: input.walletNetwork,
  });

  await recordWalletMovement({
    walletId: wallet.id,
    settlementId: job.settlement_id ?? undefined,
    amount: input.amount,
    direction: "debit",
    txHash: input.txHash,
    metadata: { jobId: input.jobId },
  });

  await db.transaction(async (trx) => {
    await trx("settlement_jobs").where({ id: input.jobId }).update({
      status: "succeeded",
      error_message: null,
      updated_at: new Date(),
    });

    if (job.settlement_id) {
      await trx("settlements").where({ id: job.settlement_id }).update({
        status: "settled",
        settled_at: new Date(),
        updated_at: new Date(),
        tx_hash: input.txHash ?? null,
      });
    }
  });

  await refreshQueueGauge();
};

export const markJobFailed = async (jobId: string, message: string) => {
  await db("settlement_jobs").where({ id: jobId }).update({
    status: "failed",
    error_message: message,
    updated_at: new Date(),
  });
  await refreshQueueGauge();
};

export const refreshQueueGauge = async () => {
  const { count } =
    (await db("settlement_jobs")
      .where({ status: "queued" })
      .count<{ count: string }>("id as count")
      .first()) ?? { count: "0" };
  settlementQueueGauge.set(Number(count));
};

const refreshFlaggedGauge = async () => {
  const { count } =
    (await db("settlement_flagged_events")
      .count<{ count: string }>("id as count")
      .first()) ?? { count: "0" };
  flaggedOffGauge.set(Number(count));
};

const mapJob = (row: SettlementJobRow): SettlementJob => ({
  id: row.id,
  settlementId: row.settlement_id,
  status: row.status,
  payload: row.payload,
  attempts: row.attempts,
  errorMessage: row.error_message,
  createdAt: row.created_at,
  updatedAt: row.updated_at,
});

const ensureAlertRuleId = async (): Promise<string> => {
  const existing = await db("alert_rules")
    .where({ name: AUTO_SETTLEMENT_ALERT_NAME })
    .first();
  if (existing) {
    return existing.id;
  }
  const [inserted] = await db("alert_rules")
    .insert({
      id: randomUUID(),
      name: AUTO_SETTLEMENT_ALERT_NAME,
      metric_key: "auto_settlement_status",
      threshold: 0,
      window_seconds: 60,
      severity: "warning",
      debounce_seconds: 60,
      owner_email: "ops@example.com",
      is_active: true,
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("id");
  return inserted.id;
};

const flagSettlement = async (
  workItem: SettlementWorkItem,
  reason: string,
): Promise<SettlementResult> => {
  await db("settlement_flagged_events").insert({
    id: randomUUID(),
    rfq_id: workItem.rfqId,
    quote_id: workItem.quoteId,
    fill_id: workItem.fillId,
    reason,
    auto_settlement_enabled: false,
    metadata: { notional: workItem.notional },
    created_at: new Date(),
    updated_at: new Date(),
  });
  settlementFlaggedCounter.inc({ reason });
  await refreshFlaggedGauge();
  const ruleId = await ensureAlertRuleId();
  await emitAlert({
    ruleId,
    severity: "warning",
    details: { reason, rfqId: workItem.rfqId, quoteId: workItem.quoteId },
  });
  return "flagged";
};

const createSettlementJob = async (
  workItem: SettlementWorkItem,
): Promise<SettlementResult> => {
  const [settlement] = await db("settlements")
    .insert({
      id: randomUUID(),
      fill_id: workItem.fillId,
      status: "queued",
      retry_count: 0,
      metadata: { notional: workItem.notional },
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");

  await db("settlement_jobs").insert({
    id: randomUUID(),
    settlement_id: settlement.id,
    status: "queued",
    payload: {
      rfqId: workItem.rfqId,
      quoteId: workItem.quoteId,
      fillId: workItem.fillId,
      notional: workItem.notional,
    },
    attempts: 0,
    created_at: new Date(),
    updated_at: new Date(),
  });

  await refreshQueueGauge();
  return "queued";
};

const processSettlementWorkItem = async (
  workItem: SettlementWorkItem,
): Promise<SettlementResult> => {
  const enabled = await isAutoSettlementEnabled();
  autoSettlementStatusGauge.set(enabled ? 1 : 0);
  if (!enabled) {
    return flagSettlement(workItem, "AUTO_SETTLEMENT_DISABLED");
  }
  return createSettlementJob(workItem);
};

export const scheduleSettlementWorkItem = async (
  workItem: SettlementWorkItem,
  options?: { forceSync?: boolean; onComplete?: (result: SettlementResult) => void },
): Promise<SettlementResult | void> => {
  const shouldRunSync =
    options?.forceSync || process.env.NODE_ENV === "test";
  if (shouldRunSync) {
    const result = await processSettlementWorkItem(workItem);
    options?.onComplete?.(result);
    return result;
  }
  setImmediate(async () => {
    try {
      const result = await processSettlementWorkItem(workItem);
      options?.onComplete?.(result);
    } catch (error) {
      logger.error(
        { err: error, workItem },
        "Failed to enqueue settlement work item",
      );
    }
  });
  return undefined;
};
