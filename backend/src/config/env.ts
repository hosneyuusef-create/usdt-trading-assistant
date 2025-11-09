import { config as loadEnv } from "dotenv";
import { z } from "zod";

loadEnv();

const envSchema = z.object({
  NODE_ENV: z
    .enum(["development", "test", "production"])
    .default("development"),
  PORT: z.coerce.number().default(9090),
  DB_URL: z.string().url(),
  TEST_DB_URL: z.string().url().optional(),
  JWT_SECRET: z.string().min(32, "JWT_SECRET must be at least 32 chars"),
  TELEGRAM_BOT_TOKEN: z.string().optional(),
  TELEGRAM_WEBHOOK_SECRET: z.string().optional(),
  AUTO_SETTLEMENT_ENABLED: z.coerce.boolean().default(false),
  LOG_LEVEL: z.string().default("info"),
  PROMETHEUS_METRICS_KEY: z.string().optional(),
  PRIMARY_APPROVER_EMAIL: z.string().email().optional(),
  SECONDARY_APPROVER_EMAIL: z.string().email().optional(),
  ALERT_OWNER_EMAIL: z.string().email().default("alerts@example.com"),
  ALERT_QUEUE_THRESHOLD: z.coerce.number().min(1).default(50),
  ALERT_FLAGGED_THRESHOLD: z.coerce.number().min(1).default(5),
  ALERT_ERROR_THRESHOLD: z.coerce.number().min(1).default(5),
  ALERT_DEBOUNCE_SECONDS: z.coerce.number().min(5).default(60),
});

export type EnvConfig = z.infer<typeof envSchema>;

export const env: EnvConfig = envSchema.parse(process.env);
