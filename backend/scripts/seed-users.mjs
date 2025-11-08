import { config as loadEnv } from "dotenv";
import knex from "knex";
import bcrypt from "bcryptjs";
import { randomUUID } from "node:crypto";

loadEnv();

const main = async () => {
  if (!process.env.DB_URL) {
    throw new Error("DB_URL is required");
  }

  const db = knex({
    client: "pg",
    connection: process.env.DB_URL,
  });

  try {
    const passwordHash = await bcrypt.hash("ChangeMe123!", 12);
    const now = new Date();

    await db("users")
      .insert({
        id: randomUUID(),
        email: "admin@example.com",
        first_name: "Admin",
        last_name: "User",
        role: "admin",
        status: "approved",
        hashed_password: passwordHash,
        metadata: {},
        created_at: now,
        updated_at: now,
      })
      .onConflict("email")
      .merge({
        role: "admin",
        status: "approved",
        hashed_password: passwordHash,
        updated_at: now,
      });

    console.log("Seeded admin user admin@example.com (password: ChangeMe123!)");
  } finally {
    await db.destroy();
  }
};

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
