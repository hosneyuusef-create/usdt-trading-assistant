import {
  Counter,
  Gauge,
  Registry,
  collectDefaultMetrics,
} from "prom-client";

export const metricsRegistry = new Registry();
collectDefaultMetrics({ register: metricsRegistry });

export const rfqVolumeCounter = new Counter({
  name: "rfq_volume_total",
  help: "Total RFQs created",
  labelNames: ["asset", "side"],
  registers: [metricsRegistry],
});

export const settlementQueueGauge = new Gauge({
  name: "settlement_queue_size",
  help: "Current number of settlements waiting for processing",
  registers: [metricsRegistry],
});

export const flaggedOffGauge = new Gauge({
  name: "flagged_off_total",
  help: "Count of operations flagged off due to feature toggles",
  registers: [metricsRegistry],
});

export const settlementFlaggedCounter = new Counter({
  name: "settlement_flagged_total",
  help: "Total settlements flagged while AUTO_SETTLEMENT is disabled",
  labelNames: ["reason"],
  registers: [metricsRegistry],
});

export const autoSettlementStatusGauge = new Gauge({
  name: "auto_settlement_status",
  help: "1 when AUTO_SETTLEMENT is enabled, 0 when disabled",
  registers: [metricsRegistry],
});

export const walletBalanceGauge = new Gauge({
  name: "wallet_balance_total",
  help: "Sum of wallet balances by network",
  labelNames: ["network"],
  registers: [metricsRegistry],
});

export const errorGauge = new Gauge({
  name: "backend_error_gauge",
  help: "Latest error indicator (1=error)",
  labelNames: ["module"],
  registers: [metricsRegistry],
});

export const alertRateCounter = new Counter({
  name: "alert_rate_total",
  help: "Alerts emitted by severity",
  labelNames: ["severity"],
  registers: [metricsRegistry],
});

export const alertThrottleCounter = new Counter({
  name: "alert_throttle_total",
  help: "Alerts skipped because of debounce/rate-limiting",
  labelNames: ["rule_id"],
  registers: [metricsRegistry],
});

export const queueLatencyGauge = new Gauge({
  name: "settlement_queue_latency_ms",
  help: "Average latency per settlement queue",
  labelNames: ["queue"],
  registers: [metricsRegistry],
});

export const metricsRender = async () => metricsRegistry.metrics();
