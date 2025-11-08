const path = require("path");
const { config: loadEnv } = require("dotenv");

loadEnv({ path: path.resolve(process.cwd(), ".env") });

const migrationsDir = path.join(__dirname, "migrations");
const seedsDir = path.join(__dirname, "seeds");

const shared = {
  client: "pg",
  migrations: {
    directory: migrationsDir,
    extension: "cjs",
    loadExtensions: [".cjs"],
  },
  seeds: {
    directory: seedsDir,
  },
  pool: {
    min: 2,
    max: 10,
  },
};

const developmentUrl =
  process.env.DB_URL ??
  "postgres://postgres:postgres@127.0.0.1:5432/usdt_trading_dev";
const testUrl =
  process.env.TEST_DB_URL ??
  process.env.DB_URL ??
  "postgres://postgres:postgres@127.0.0.1:5432/usdt_trading_test";

const config = {
  development: {
    ...shared,
    connection: developmentUrl,
  },
  test: {
    ...shared,
    connection: testUrl,
  },
  production: {
    ...shared,
    connection: process.env.DB_URL ?? developmentUrl,
    pool: {
      min: 2,
      max: 20,
    },
  },
};

module.exports = config;
