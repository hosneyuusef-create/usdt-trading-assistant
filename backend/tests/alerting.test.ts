import { describe, expect, it } from "vitest";
import { db } from "../src/database/client.js";
import { env } from "../src/config/env.js";
import {
  ensureAlertRule,
  emitAlert,
  maybeEmitQueueAlert,
} from "../src/domain/alerting.js";

const countEvents = async (ruleId: string): Promise<number> => {
  const { count } =
    (await db("alert_events")
      .where({ rule_id: ruleId })
      .count<{ count: string }>("id as count")
      .first()) ?? { count: "0" };
  return Number(count);
};

describe("alerting", () => {
  it("debounces duplicate alerts for the same rule", async () => {
    const rule = await ensureAlertRule({
      name: "test_debounce_rule",
      metricKey: "test_metric",
      threshold: 1,
      severity: "warning",
      debounceSeconds: 120,
      ownerEmail: "alerts@example.com",
    });

    await emitAlert({
      ruleId: rule.id,
      severity: "warning",
      details: { attempt: 1 },
    });
    await emitAlert({
      ruleId: rule.id,
      severity: "warning",
      details: { attempt: 2 },
    });

    expect(await countEvents(rule.id)).toBe(1);
  });

  it("emits queue alert when threshold is exceeded", async () => {
    const originalThreshold = env.ALERT_QUEUE_THRESHOLD;
    env.ALERT_QUEUE_THRESHOLD = 1;
    try {
      await maybeEmitQueueAlert(2);
      const rule = await db("alert_rules")
        .where({ name: "settlement_queue_backlog" })
        .first();
      expect(rule).toBeDefined();
      expect(await countEvents(rule.id)).toBe(1);
    } finally {
      env.ALERT_QUEUE_THRESHOLD = originalThreshold;
    }
  });
});
