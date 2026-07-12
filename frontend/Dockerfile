# ---- deps: install dependencies only, cached separately from source changes ----
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ---- builder: produce the Next.js standalone production build ----
FROM node:20-alpine AS builder
WORKDIR /app

# Browser-side requests must reach a URL the host machine can resolve, so the
# published backend port (not an internal Docker service name) is the correct
# default for a local docker-compose setup.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runner: minimal image with only the standalone server output ----
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# PORT defaults to 3000 for local/docker-compose use; Railway (and most
# PaaS hosts) inject their own PORT at runtime, which this default is
# overridden by — the Next.js standalone server.js already reads
# process.env.PORT itself, so only the healthcheck needs to follow suit.
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:' + (process.env.PORT || 3000) + '/', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
