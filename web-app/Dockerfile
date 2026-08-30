# Build stage
FROM node:22.23.2-slim AS builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN pnpm run build

# Production stage
FROM node:22.23.2-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

# Must exist and belong to `node` before the COPYs below land in it: COPY
# would otherwise create it root-owned, and mounting next_cache at
# .next/cache does nothing for its parent. Measured: uid 1000 cannot write a
# root-owned /app/.next. The cache mount itself needs no ownership fix - it
# is tmpfs, which comes up 1777.
RUN mkdir .next && chown node:node .next

# Copy necessary files from builder
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

# Drop privileges. Every other service in the stack does; this one is last.
# `node` (uid 1000) ships with the base image, so there is no user to create.
USER node

# Expose port
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start the application
CMD ["node", "server.js"]
