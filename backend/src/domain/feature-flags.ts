import { db } from "../database/client.js";
import { env } from "../config/env.js";

export const isFlagEnabled = async (
  key: string,
  fallback?: boolean,
): Promise<boolean> => {
  const record = await db("feature_flags").where({ key }).first();
  if (record) {
    return Boolean(record.is_enabled);
  }
  if (key === "AUTO_SETTLEMENT_ENABLED") {
    return env.AUTO_SETTLEMENT_ENABLED;
  }
  return fallback ?? false;
};

export const isAutoSettlementEnabled = async (): Promise<boolean> => {
  if (process.env.AUTO_SETTLEMENT_ENABLED !== undefined) {
    return process.env.AUTO_SETTLEMENT_ENABLED === "true";
  }
  return isFlagEnabled("AUTO_SETTLEMENT_ENABLED", env.AUTO_SETTLEMENT_ENABLED);
};

export const setFlag = async (key: string, enabled: boolean) => {
  const exists = await db("feature_flags").where({ key }).first();
  if (exists) {
    await db("feature_flags")
      .where({ key })
      .update({ is_enabled: enabled, updated_at: new Date() });
  } else {
    await db("feature_flags").insert({
      key,
      is_enabled: enabled,
      created_at: new Date(),
      updated_at: new Date(),
    });
  }
};
