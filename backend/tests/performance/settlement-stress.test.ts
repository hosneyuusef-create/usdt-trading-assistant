import { randomUUID } from "node:crypto";
import bcrypt from "bcryptjs";
import { performance } from "node:perf_hooks";
import { describe, expect, it } from "vitest";
import { db } from "../../src/database/client.js";
import { scheduleSettlementWorkItem } from "../../src/domain/settlement.js";

const insertUser = async (email: string) => {
  const [user] = await db("users")
    .insert({
      email,
      first_name: "Perf",
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

const insertTestGraph = async (notional: number) => {
  const user = await insertUser(`perf+${randomUUID()}@example.com`);
  const rfqId = randomUUID();
  const quoteId = randomUUID();
  const fillId = randomUUID();

  await db("rfqs").insert({
    id: rfqId,
    user_id: user.id,
    asset: "USDT",
    notional,
    side: "buy",
    status: "accepted",
    expires_at: new Date(Date.now() + 60000),
    metadata: {},
    created_at: new Date(),
    updated_at: new Date(),
  });

  await db("quotes").insert({
    id: quoteId,
    rfq_id: rfqId,
    liquidity_provider_id: null,
    price: 1,
    spread_bps: 1,
    status: "accepted",
    valid_until: new Date(Date.now() + 60000),
    created_at: new Date(),
    updated_at: new Date(),
  });

  await db("fills").insert({
    id: fillId,
    quote_id: quoteId,
    fill_amount: notional,
    status: "pending",
    metadata: {},
    created_at: new Date(),
    updated_at: new Date(),
  });

  return { rfqId, quoteId, fillId, notional };
};

describe("settlement performance", () => {
  it(
    "processes flag-off then flag-on batches under 120s",
    async () => {
      const iterations = 40;

      const start = performance.now();

      process.env.AUTO_SETTLEMENT_ENABLED = "false";
      let flaggedCount = 0;
      for (let i = 0; i < iterations; i++) {
        const graph = await insertTestGraph(100 + i);
        await scheduleSettlementWorkItem(
          {
            rfqId: graph.rfqId,
            quoteId: graph.quoteId,
            fillId: graph.fillId,
            notional: graph.notional,
          },
          {
            forceSync: true,
            onComplete: (result) => {
              if (result === "flagged") flaggedCount += 1;
            },
          },
        );
      }

      expect(flaggedCount).toBe(iterations);

      process.env.AUTO_SETTLEMENT_ENABLED = "true";
      let queuedCount = 0;
      for (let i = 0; i < iterations; i++) {
        const graph = await insertTestGraph(200 + i);
        await scheduleSettlementWorkItem(
          {
            rfqId: graph.rfqId,
            quoteId: graph.quoteId,
            fillId: graph.fillId,
            notional: graph.notional,
          },
          {
            forceSync: true,
            onComplete: (result) => {
              if (result === "queued") queuedCount += 1;
            },
          },
        );
      }

      expect(queuedCount).toBe(iterations);

      const duration = performance.now() - start;
      expect(duration).toBeLessThan(120000);
    },
    120000,
  );
});
