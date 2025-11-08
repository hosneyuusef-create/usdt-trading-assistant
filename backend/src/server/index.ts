import Fastify, { type FastifyError } from "fastify";
import {
  serializerCompiler,
  validatorCompiler,
  type ZodTypeProvider,
} from "fastify-type-provider-zod";
import cors from "@fastify/cors";
import helmet from "@fastify/helmet";
import rateLimit from "@fastify/rate-limit";
import sensible from "@fastify/sensible";
import { env } from "../config/env.js";
import { logger } from "../utils/logger.js";
import { healthRoutes } from "../routes/health.js";
import { metricsRoutes } from "../routes/metrics.js";
import { userRoutes } from "../routes/users.js";
import { dualControlRoutes } from "../routes/dual-control.js";
import { rfqRoutes } from "../routes/rfqs.js";
import { settlementRoutes } from "../routes/settlements.js";
import { startTelegramBot } from "../telegram/bot.js";
import { ZodError } from "zod";
import { DomainError } from "../utils/errors.js";

const isFastifyValidationError = (
  error: unknown,
): error is FastifyError & { validation?: unknown } => {
  if (!error || typeof error !== "object") {
    return false;
  }
  const candidate = error as FastifyError;
  return candidate.code === "FST_ERR_VALIDATION";
};

export const buildServer = () => {
  const app = Fastify({ logger }).withTypeProvider<ZodTypeProvider>();

  app.setValidatorCompiler(validatorCompiler);
  app.setSerializerCompiler(serializerCompiler);

  app.register(sensible);
  app.register(cors, { origin: true });
  app.register(helmet);
  app.register(rateLimit, { max: 200, timeWindow: "1 minute" });

  app.setErrorHandler((error, _request, reply) => {
    if (error instanceof DomainError) {
      reply.status(error.statusCode).send({ message: error.message });
      return;
    }
    if (error instanceof ZodError || isFastifyValidationError(error)) {
      const details = error instanceof ZodError ? error.issues : error.validation;
      reply.status(400).send({
        message: "Validation failed",
        details,
      });
      return;
    }
    logger.error(error, "Unhandled error");
    reply.status(500).send({ message: "Internal server error" });
  });

  app.register(healthRoutes);
  app.register(metricsRoutes);
  app.register(userRoutes);
  app.register(dualControlRoutes);
  app.register(rfqRoutes);
  app.register(settlementRoutes);

  app.addHook("onReady", () => {
    if (env.NODE_ENV !== "test") {
      startTelegramBot();
    }
  });

  return app;
};

export const start = async () => {
  const server = buildServer();
  await server.listen({ port: env.PORT, host: "0.0.0.0" });
  logger.info(`🚀 Backend listening on port ${env.PORT}`);
  return server;
};

if (process.env.NODE_ENV !== "test") {
  start().catch((error) => {
    logger.error(error, "Failed to start server");
    process.exit(1);
  });
}
