import type { FastifyInstance } from "fastify";
import fp from "fastify-plugin";
import { z } from "zod";
import {
  approveUser,
  createUser,
  listUsersByStatus,
  rejectUser,
} from "../domain/user.js";
import { DomainError } from "../utils/errors.js";

const createUserSchema = z.object({
  email: z.string().email(),
  firstName: z.string().min(1),
  lastName: z.string().min(1),
  password: z.string().min(8),
  role: z.enum(["admin", "ops", "viewer", "system"]).optional(),
  createdBy: z.string().uuid().optional(),
});

const approvalSchema = z.object({
  dualControlRequestId: z.string().uuid(),
  approverId: z.string().uuid(),
  secondaryApproverId: z.string().uuid(),
  reason: z.string().min(5, "Reason must be at least 5 characters"),
});

const plugin = async (app: FastifyInstance) => {
  app.post(
    "/api/users",
    {
      schema: {
        body: createUserSchema,
      },
    },
    async (request, reply) => {
      const body = createUserSchema.parse(request.body);
      try {
        const user = await createUser(body);
        return reply.status(201).send(user);
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );

  app.get("/api/users/pending", async (_request, reply) => {
    const users = await listUsersByStatus("pending");
    return reply.send(users);
  });

  app.get("/api/users/approved", async (_request, reply) => {
    const users = await listUsersByStatus("approved");
    return reply.send(users);
  });

  app.post(
    "/api/users/:id/approve",
    {
      schema: {
        body: approvalSchema,
      },
    },
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      const body = approvalSchema.parse(request.body);
      try {
        const user = await approveUser({
          userId: params.id,
          approverId: body.approverId,
          dualControlRequestId: body.dualControlRequestId,
          approvalReason: body.reason,
          secondaryApproverId: body.secondaryApproverId,
        });
        return reply.send(user);
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );

  app.post(
    "/api/users/:id/reject",
    {
      schema: {
        body: approvalSchema.pick({
          dualControlRequestId: true,
          approverId: true,
        }).extend({
          reason: z.string().min(5, "Reason must be at least 5 characters"),
        }),
      },
    },
    async (request, reply) => {
      const paramsSchema = z.object({ id: z.string().uuid() });
      const params = paramsSchema.parse(request.params);
      const body = approvalSchema
        .pick({ dualControlRequestId: true, approverId: true })
        .extend({
          reason: z.string().min(5, "Reason must be at least 5 characters"),
        })
        .parse(request.body);
      try {
        const user = await rejectUser({
          userId: params.id,
          approverId: body.approverId,
          dualControlRequestId: body.dualControlRequestId,
          reason: body.reason,
        });
        return reply.send(user);
      } catch (error) {
        if (error instanceof DomainError) {
          return reply.status(error.statusCode).send({ message: error.message });
        }
        throw error;
      }
    },
  );
};

export const userRoutes = fp(plugin);
