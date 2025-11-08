import type { FastifyInstance } from "fastify";
import fp from "fastify-plugin";
import { z } from "zod";
import {
  getNextSettlementJob,
  markJobFailed,
  markJobInProgress,
  markJobSucceeded,
} from "../domain/settlement.js";
import { DomainError } from "../utils/errors.js";

const succeedSchema = z.object({
  walletAddress: z.string().min(5),
  walletNetwork: z.string().min(2),
  amount: z.number().positive(),
  txHash: z.string().optional(),
});

const plugin = async (app: FastifyInstance) => {
  app.get("/api/settlements/queue/head", async (_request, reply) => {
    const job = await getNextSettlementJob();
    return reply.send(job ?? {});
  });

  app.post(
    "/api/settlements/jobs/:id/start",
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      try {
        const job = await markJobInProgress(params.id);
        return reply.send(job);
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );

  app.post(
    "/api/settlements/jobs/:id/succeed",
    {
      schema: { body: succeedSchema },
    },
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      const payload = succeedSchema.parse(request.body);
      try {
        await markJobSucceeded({
          jobId: params.id,
          walletAddress: payload.walletAddress,
          walletNetwork: payload.walletNetwork,
          amount: payload.amount,
          txHash: payload.txHash,
        });
        return reply.status(204).send();
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );

  app.post(
    "/api/settlements/jobs/:id/fail",
    {
      schema: {
        body: z.object({ message: z.string().min(3) }),
      },
    },
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      const payload = z.object({ message: z.string().min(3) }).parse(request.body);
      await markJobFailed(params.id, payload.message);
      return reply.status(204).send();
    },
  );
};

export const settlementRoutes = fp(plugin);
