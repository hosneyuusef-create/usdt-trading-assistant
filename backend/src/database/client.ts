import knex, { type Knex } from "knex";
import { env } from "../config/env.js";

const connectionString =
  env.NODE_ENV === "test"
    ? env.TEST_DB_URL ?? env.DB_URL
    : env.DB_URL;

export const db: Knex = knex({
  client: "pg",
  connection: connectionString,
  pool: {
    min: 2,
    max: env.NODE_ENV === "production" ? 20 : 10,
  },
  migrations: {
    tableName: "knex_migrations",
  },
});

export const closeDb = async () => {
  await db.destroy();
};
