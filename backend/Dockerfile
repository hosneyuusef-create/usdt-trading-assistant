FROM node:18-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY package*.json ./
RUN npm ci --omit=dev
COPY --from=builder /app/dist ./dist
COPY knexfile.cjs ./knexfile.cjs
COPY migrations ./migrations
EXPOSE 9090
CMD ["sh", "-c", "npm run migrate:dev && node dist/server/index.js"]
