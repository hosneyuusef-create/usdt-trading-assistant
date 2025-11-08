import { randomUUID } from "node:crypto";
import { db } from "../database/client.js";
import { DomainError } from "../utils/errors.js";
import { recordAuditLog } from "../utils/audit.js";
import { rfqVolumeCounter } from "./metrics.js";
import { scheduleSettlementWorkItem } from "./settlement.js";

export type RfqSide = "buy" | "sell";
export type RfqStatus =
  | "draft"
  | "quoted"
  | "accepted"
  | "expired"
  | "cancelled";

export type QuoteStatus =
  | "pending"
  | "sent"
  | "expired"
  | "accepted"
  | "rejected";

export type CreateRfqInput = {
  userId: string;
  asset: string;
  notional: number;
  side: RfqSide;
  expiresAt: Date;
};

export const createRfq = async (input: CreateRfqInput) => {
  const id = randomUUID();
  const [row] = await db("rfqs")
    .insert({
      id,
      user_id: input.userId,
      asset: input.asset,
      notional: input.notional,
      side: input.side,
      status: "draft",
      expires_at: input.expiresAt,
      metadata: {},
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");

  rfqVolumeCounter.inc({ asset: input.asset, side: input.side });

  await recordAuditLog({
    actorUserId: input.userId,
    action: "rfq_created",
    entityType: "rfq",
    entityId: id,
    metadata: { asset: input.asset, notional: input.notional },
  });

  return mapRfq(row);
};

export type CreateQuoteInput = {
  rfqId: string;
  liquidityProviderId?: string;
  price: number;
  spreadBps: number;
  validUntil: Date;
};

export const createQuote = async (input: CreateQuoteInput) => {
  const rfq = await db("rfqs").where({ id: input.rfqId }).first();
  if (!rfq) {
    throw new DomainError("RFQ not found", 404);
  }
  if (new Date(rfq.expires_at) < new Date()) {
    throw new DomainError("RFQ expired", 400);
  }

  const [quoteRow] = await db("quotes")
    .insert({
      id: randomUUID(),
      rfq_id: input.rfqId,
      liquidity_provider_id: input.liquidityProviderId ?? null,
      price: input.price,
      spread_bps: input.spreadBps,
      status: "sent",
      valid_until: input.validUntil,
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");

  await db("rfqs")
    .where({ id: input.rfqId })
    .update({ status: "quoted", updated_at: new Date() });

  return mapQuote(quoteRow);
};

export type AcceptQuoteInput = {
  quoteId: string;
  actorUserId: string;
};

export const acceptQuote = async ({
  quoteId,
  actorUserId,
}: AcceptQuoteInput) => {
  const quote = await db("quotes").where({ id: quoteId }).first();
  if (!quote) {
    throw new DomainError("Quote not found", 404);
  }
  if (quote.status !== "sent" && quote.status !== "pending") {
    throw new DomainError("Quote cannot be accepted", 409);
  }

  const rfq = await db("rfqs").where({ id: quote.rfq_id }).first();
  if (!rfq) {
    throw new DomainError("RFQ missing for quote", 500);
  }

  const fillRow = await db.transaction(async (trx) => {
    await trx("quotes").where({ id: quoteId }).update({
      status: "accepted",
      updated_at: new Date(),
    });
    await trx("rfqs").where({ id: quote.rfq_id }).update({
      status: "accepted",
      updated_at: new Date(),
    });

    const [fill] = await trx("fills")
      .insert({
        id: randomUUID(),
        quote_id: quote.id,
        fill_amount: rfq.notional,
        status: "pending",
        metadata: {},
        created_at: new Date(),
        updated_at: new Date(),
      })
      .returning("*");

    return fill;
  });

  await scheduleSettlementWorkItem(
    {
      rfqId: quote.rfq_id,
      quoteId: quote.id,
      fillId: fillRow.id,
      notional: Number(rfq.notional),
    },
    { forceSync: process.env.NODE_ENV === "test" },
  );

  await recordAuditLog({
    actorUserId: actorUserId,
    action: "quote_accepted",
    entityType: "quote",
    entityId: quoteId,
  });
};

const mapRfq = (row: Record<string, any>) => ({
  id: row.id,
  userId: row.user_id,
  asset: row.asset,
  notional: Number(row.notional),
  side: row.side,
  status: row.status,
  expiresAt: row.expires_at,
  createdAt: row.created_at,
  updatedAt: row.updated_at,
});

const mapQuote = (row: Record<string, any>) => ({
  id: row.id,
  rfqId: row.rfq_id,
  liquidityProviderId: row.liquidity_provider_id,
  price: Number(row.price),
  spreadBps: Number(row.spread_bps),
  status: row.status,
  validUntil: row.valid_until,
  createdAt: row.created_at,
  updatedAt: row.updated_at,
});
