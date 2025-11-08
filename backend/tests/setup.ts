import { config as loadEnv } from "dotenv";
import fs from "node:fs";
import path from "node:path";
import { afterAll, beforeEach } from "vitest";
import { db } from "../src/database/client.js";

const envFile = fs.existsSync(path.resolve(process.cwd(), ".env.test"))
  ? ".env.test"
  : ".env";
loadEnv({ path: path.resolve(process.cwd(), envFile) });

beforeEach(async () => {
  process.env.AUTO_SETTLEMENT_ENABLED = "true";
  await truncateAllTables();
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
