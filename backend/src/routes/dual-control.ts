import type { FastifyInstance } from "fastify";
import fp from "fastify-plugin";
import { z } from "zod";
import {
  listPendingDualControlRequests,
  resolveDualControlRequest,
} from "../domain/dual-control.js";
import { DomainError } from "../utils/errors.js";

const resolveSchema = z.object({
  approverId: z.string().uuid(),
  approve: z.boolean(),
  secondaryApproverId: z.string().uuid().optional(),
  approvalReason: z.string().min(5).optional(),
  rejectionReason: z.string().optional(),
});

const plugin = async (app: FastifyInstance) => {
  app.get("/api/dual-control/requests", async (_request, reply) => {
    const requests = await listPendingDualControlRequests();
    return reply.send(requests);
  });

  app.post(
    "/api/dual-control/:id/resolve",
    {
      schema: {
        body: resolveSchema,
      },
    },
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      const payload = resolveSchema.parse(request.body);
      try {
        const updated = await resolveDualControlRequest({
          requestId: params.id,
          approverId: payload.approverId,
          secondaryApproverId: payload.secondaryApproverId,
          approvalReason: payload.approvalReason,
          approve: payload.approve,
          rejectionReason: payload.rejectionReason,
        });
        return reply.send(updated);
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );
};

export const dualControlRoutes = fp(plugin);
