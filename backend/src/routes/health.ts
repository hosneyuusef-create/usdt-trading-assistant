import type { FastifyInstance } from "fastify";
import fp from "fastify-plugin";
import { db } from "../database/client.js";

const plugin = async (app: FastifyInstance) => {
  app.get("/health", async () => {
    await db.raw("select 1");
    return {
      status: "ok",
      timestamp: new Date().toISOString(),
    };
  });
};

export const healthRoutes = fp(plugin);
