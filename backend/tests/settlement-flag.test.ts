import bcrypt from "bcryptjs";
import { describe, expect, it, beforeEach } from "vitest";
import { db } from "../src/database/client.js";
import { createRfq, createQuote, acceptQuote } from "../src/domain/rfq.js";

const insertApprovedUser = async (email: string) => {
  const [user] = await db("users")
    .insert({
      email,
      first_name: "Ops",
      last_name: "User",
      role: "ops",
      status: "approved",
      hashed_password: await bcrypt.hash("Password123!", 10),
      metadata: {},
      created_at: new Date(),
      updated_at: new Date(),
    })
    .returning("*");
  return user;
};

const insertLiquidityProvider = async () => {
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

describe("AUTO_SETTLEMENT flag behavior", () => {
  beforeEach(async () => {
    process.env.AUTO_SETTLEMENT_ENABLED = "true";
    await db("settlement_jobs").del();
    await db("settlement_flagged_events").del();
  });

  it("queues settlement job when flag enabled", async () => {
    const user = await insertApprovedUser("flag-enabled@example.com");
    const lp = await insertLiquidityProvider();

    const rfq = await createRfq({
      userId: user.id,
      asset: "USDT",
      notional: 1000,
      side: "buy",
      expiresAt: new Date(Date.now() + 60000),
    });

    const quote = await createQuote({
      rfqId: rfq.id,
      liquidityProviderId: lp.id,
      price: 1,
      spreadBps: 5,
      validUntil: new Date(Date.now() + 30000),
    });

    await acceptQuote({ quoteId: quote.id, actorUserId: user.id });

    const jobs = await db("settlement_jobs").select("*");
    expect(jobs).toHaveLength(1);
    expect(jobs[0].status).toBe("queued");
  });

  it("flags settlement when AUTO_SETTLEMENT is disabled", async () => {
    process.env.AUTO_SETTLEMENT_ENABLED = "false";

    const user = await insertApprovedUser("flag-disabled@example.com");
    const lp = await insertLiquidityProvider();

    const rfq = await createRfq({
      userId: user.id,
      asset: "USDT",
      notional: 500,
      side: "sell",
      expiresAt: new Date(Date.now() + 60000),
    });

    const quote = await createQuote({
      rfqId: rfq.id,
      liquidityProviderId: lp.id,
      price: 1,
      spreadBps: 3,
      validUntil: new Date(Date.now() + 30000),
    });

    await acceptQuote({ quoteId: quote.id, actorUserId: user.id });

    const jobs = await db("settlement_jobs")
      .where({ status: "queued" })
      .select("*");
    expect(jobs).toHaveLength(0);

    const fill = await db("fills").where({ quote_id: quote.id }).first();
    const flagged = await db("settlement_flagged_events")
      .where({ fill_id: fill.id })
      .select("*");

    expect(flagged).toHaveLength(1);
    expect(flagged[0].reason).toBe("AUTO_SETTLEMENT_DISABLED");
  });
});
