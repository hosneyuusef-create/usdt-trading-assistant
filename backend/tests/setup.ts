import { config as loadEnv } from "dotenv";
import fs from "node:fs";
import path from "node:path";
import { afterAll, afterEach, beforeEach } from "vitest";
import { db } from "../src/database/client.js";

const envFile = fs.existsSync(path.resolve(process.cwd(), ".env.test"))
  ? ".env.test"
  : ".env";
loadEnv({ path: path.resolve(process.cwd(), envFile) });

const GLOBAL_LOCK_KEY = 42;

beforeEach(async () => {
  await db.raw("SELECT pg_advisory_lock(?)", [GLOBAL_LOCK_KEY]);
  try {
    process.env.AUTO_SETTLEMENT_ENABLED = "true";
    await truncateAllTables();
  } catch (error) {
    await db.raw("SELECT pg_advisory_unlock(?)", [GLOBAL_LOCK_KEY]);
    throw error;
  }
});

afterEach(async () => {
  await db.raw("SELECT pg_advisory_unlock(?)", [GLOBAL_LOCK_KEY]);
});

afterAll(async () => {
  await db.destroy();
});

const truncateAllTables = async () => {
  const tables = await db("pg_tables")
    .select("tablename")
    .where({ schemaname: "public" });
  const tableNames = tables
    .map((record) => record.tablename)
    .filter((name) => !["knex_migrations", "knex_migrations_lock"].includes(name));
  if (!tableNames.length) {
    return;
  }
  const joined = tableNames.map((name) => `"${name}"`).join(", ");
  await db.raw(`TRUNCATE TABLE ${joined} RESTART IDENTITY CASCADE`);
};
