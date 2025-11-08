import type { FastifyInstance } from "fastify";
import fp from "fastify-plugin";
import { z } from "zod";
import { acceptQuote, createQuote, createRfq } from "../domain/rfq.js";
import { DomainError } from "../utils/errors.js";

const createRfqBody = z.object({
  userId: z.string().uuid(),
  asset: z.string().min(1),
  notional: z.number().positive(),
  side: z.enum(["buy", "sell"]),
  expiresAt: z.coerce.date(),
});

const createQuoteBody = z.object({
  price: z.number().positive(),
  spreadBps: z.number().nonnegative(),
  liquidityProviderId: z.string().uuid().optional(),
  validUntil: z.coerce.date(),
});

const acceptQuoteBody = z.object({
  actorUserId: z.string().uuid(),
});

const plugin = async (app: FastifyInstance) => {
  app.post(
    "/api/rfqs",
    {
      schema: {
        body: createRfqBody,
      },
    },
    async (request, reply) => {
      const payload = createRfqBody.parse(request.body);
      try {
        const rfq = await createRfq(payload);
        return reply.status(201).send(rfq);
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );

  app.post(
    "/api/rfqs/:id/quotes",
    {
      schema: {
        body: createQuoteBody,
      },
    },
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      const payload = createQuoteBody.parse(request.body);
      try {
        const quote = await createQuote({
          ...payload,
          rfqId: params.id,
        });
        return reply.status(201).send(quote);
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );

  app.post(
    "/api/quotes/:id/accept",
    {
      schema: {
        body: acceptQuoteBody,
      },
    },
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      const payload = acceptQuoteBody.parse(request.body);
      try {
        await acceptQuote({
          quoteId: params.id,
          actorUserId: payload.actorUserId,
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
};

export const rfqRoutes = fp(plugin);
