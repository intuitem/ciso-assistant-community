ARG NODE_BUILD_IMAGE=dhi.io/node:24-dev
ARG NODE_RUNTIME_IMAGE=dhi.io/node:24
FROM ${NODE_BUILD_IMAGE} AS builder
ENV NODE_OPTIONS="--max-old-space-size=10240"
WORKDIR /app

ENV PUBLIC_BACKEND_API_URL=foo

COPY package*.json ./
COPY . .
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile
RUN pnpm run build
RUN pnpm prune

# DHI runtime image: distroless (no shell/package manager), runs as uid 1000
FROM ${NODE_RUNTIME_IMAGE}
ENV NODE_OPTIONS="--max-old-space-size=10240"
WORKDIR /app
COPY --from=builder --chown=1000:1000 /app/build build/
COPY --from=builder --chown=1000:1000 /app/server server/
COPY --from=builder --chown=1000:1000 /app/node_modules node_modules/
COPY --chown=1000:1000 package.json .
EXPOSE 3000
ENV NODE_ENV=production
ENV BODY_SIZE_LIMIT=25000000

CMD [ "node", "server" ]
