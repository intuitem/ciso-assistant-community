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

# Install the exact pnpm version pinned by packageManager: a mismatched pnpm
# delegates to the pinned version via @pnpm/exe, a native binary that needs
# libatomic.so.1, which the DHI image doesn't ship.
RUN npm install -g "pnpm@$(node -p "require('./package.json').packageManager.split('@')[1]")"
RUN pnpm install --frozen-lockfile
RUN pnpm run build
RUN pnpm prune

# Distroless runtime: no shell, no package manager, no npm. The copies are chowned
# rather than a user being created, since groupadd/useradd need a shell.
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

# uid 1000 is `node` in the runtime image; set explicitly so the image is non-root
# on its own, whatever NODE_RUNTIME_IMAGE is overridden with.
USER 1000:1000

CMD [ "node", "server" ]
