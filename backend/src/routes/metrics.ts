import type { FastifyInstance } from "fastify";
import fp from "fastify-plugin";
import { metricsRender } from "../domain/metrics.js";
import { env } from "../config/env.js";

const plugin = async (app: FastifyInstance) => {
  app.get("/metrics", async (request, reply) => {
    if (env.PROMETHEUS_METRICS_KEY) {
      const authHeader = request.headers.authorization;
      if (
        !authHeader ||
        authHeader !== `Bearer ${env.PROMETHEUS_METRICS_KEY}`
      ) {
        return reply.status(401).send({ error: "invalid metrics token" });
      }
    }
    reply.header("Content-Type", "text/plain");
    return metricsRender();
  });
};

export const metricsRoutes = fp(plugin);
