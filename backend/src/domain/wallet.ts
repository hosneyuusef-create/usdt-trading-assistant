import { randomUUID } from "node:crypto";
import { db } from "../database/client.js";
import { walletBalanceGauge } from "./metrics.js";

export type WalletInput = {
  label: string;
  address: string;
  network: string;
};

export const ensureWallet = async (input: WalletInput) => {
  const existingWallet = await db("wallets")
    .where({ address: input.address })
    .first();
  if (existingWallet) {
    return existingWallet;
  }
  const [inserted] = await db("wallets")
    .insert({
      id: randomUUID(),
      label: input.label,
      address: input.address,
      network: input.network,
      balance: 0,
      status: "active",
      metadata: {},
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");
  await refreshWalletMetrics();
  return inserted;
};

export type WalletMovement = {
  walletId: string;
  settlementId?: string;
  amount: number;
  currency?: string;
  direction: "credit" | "debit";
  txHash?: string;
  metadata?: Record<string, unknown>;
};

export const recordWalletMovement = async (movement: WalletMovement) => {
  await db("wallet_transactions").insert({
    id: randomUUID(),
    wallet_id: movement.walletId,
    settlement_id: movement.settlementId ?? null,
    amount: movement.amount,
    direction: movement.direction,
    currency: movement.currency ?? "USDT",
    tx_hash: movement.txHash ?? null,
    status: "confirmed",
    metadata: movement.metadata ?? {},
    created_at: new Date(),
    updated_at: new Date(),
  });

  const operator = movement.direction === "credit" ? 1 : -1;
  await db("wallets")
    .where({ id: movement.walletId })
    .update({
      balance: db.raw("balance + ?", [operator * movement.amount]),
      updated_at: new Date(),
    });

  await refreshWalletMetrics();
};

export const refreshWalletMetrics = async () => {
  type WalletBalanceRow = { network: string; total?: string | number | null };
  const balances = await db<WalletBalanceRow>("wallets")
    .select("network")
    .sum({ total: "balance" })
    .groupBy("network");
  walletBalanceGauge.reset();
  for (const record of balances) {
    walletBalanceGauge.set(
      { network: record.network },
      Number(record.total ?? 0),
    );
  }
};
