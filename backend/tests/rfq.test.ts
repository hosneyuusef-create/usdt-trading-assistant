import bcrypt from "bcryptjs";
import { describe, expect, it } from "vitest";
import { db } from "../src/database/client.js";
import { createQuote, createRfq, acceptQuote } from "../src/domain/rfq.js";

const insertUser = async () => {
  const [row] = await db("users")
    .insert({
      email: `trader+${Date.now()}@example.com`,
      first_name: "Trader",
      last_name: "One",
      role: "ops",
      status: "approved",
      hashed_password: await bcrypt.hash("Password123", 8),
      metadata: {},
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");
  return row;
};

const insertLp = async () => {
  const [lp] = await db("liquidity_providers")
    .insert({
      name: `LP-${Date.now()}`,
      status: "active",
      metadata: {},
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");
  return lp;
};

describe("RFQ domain", () => {
  it("creates RFQ, quote, and settlement job", async () => {
    const user = await insertUser();
    const lp = await insertLp();

    const rfq = await createRfq({
      userId: user.id,
      asset: "USDT",
      notional: 100000,
      side: "buy",
      expiresAt: new Date(Date.now() + 5 * 60 * 1000),
    });
    expect(rfq.status).toBe("draft");

    const quote = await createQuote({
      rfqId: rfq.id,
      liquidityProviderId: lp.id,
      price: 1.0,
      spreadBps: 5,
      validUntil: new Date(Date.now() + 2 * 60 * 1000),
    });
    expect(quote.status).toBe("sent");

    await acceptQuote({
      quoteId: quote.id,
      actorUserId: user.id,
    });

    const settlementJob = await db("settlement_jobs").first();
    expect(settlementJob).toBeDefined();
    expect(settlementJob.status).toBe("queued");
  });
});
