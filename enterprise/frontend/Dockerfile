# Docker Hardened Images via the GHCR mirror, not dhi.io: DHI's free tier serves
# anonymous pulls, so dhi.io 401s for anyone logged in to Docker Hub.
ARG NODE_BUILD_IMAGE=ghcr.io/intuitem/ciso-assistant-community/mirror/dhi-node:24-dev
ARG NODE_RUNTIME_IMAGE=ghcr.io/intuitem/ciso-assistant-community/mirror/dhi-node:24

FROM ${NODE_BUILD_IMAGE} AS builder
ENV NODE_OPTIONS="--max-old-space-size=10240"
WORKDIR /app

ENV PUBLIC_BACKEND_API_URL=foo

COPY package*.json ./
COPY project.inlang .
COPY . .
COPY --from=enterprise_frontend / .

RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile
RUN pnpm run build
RUN pnpm prune

# Distroless runtime: no shell, no package manager, no npm. Runs as uid 1000, so
# the copies are chowned rather than a user being created (groupadd needs a shell).
FROM ${NODE_RUNTIME_IMAGE}
ENV NODE_OPTIONS="--max-old-space-size=10240"
WORKDIR /app
COPY --from=builder --chown=1000:1000 /app/build build/
COPY --from=builder --chown=1000:1000 /app/server server/
COPY --from=builder --chown=1000:1000 /app/node_modules node_modules/
COPY --chown=1000:1000 package.json .
EXPOSE 3000
ENV NODE_ENV=production
ENV BODY_SIZE_LIMIT=50000000

CMD [ "node", "server" ]
