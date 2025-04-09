FROM node:22-slim AS builder
ENV NODE_OPTIONS="--max-old-space-size=8192"
WORKDIR /app

ENV PUBLIC_BACKEND_API_URL=foo

COPY frontend/package*.json ./
COPY frontend/project.inlang .
COPY frontend/ .
COPY enterprise/frontend .

RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile
RUN pnpm run build
RUN pnpm prune

FROM node:22-slim
ENV NODE_OPTIONS="--max-old-space-size=8192"
WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/server server/
COPY --from=builder /app/node_modules node_modules/
COPY frontend/package.json .
EXPOSE 3000
ENV NODE_ENV=production
ENV BODY_SIZE_LIMIT=20000000
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid 1001 app
USER app

CMD [ "node", "server" ]
