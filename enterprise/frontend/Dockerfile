FROM node:21-alpine AS builder
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

FROM node:21-alpine
WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/server server/
COPY --from=builder /app/node_modules node_modules/
COPY frontend/package.json .
EXPOSE 3000
ENV NODE_ENV=production
ENV BODY_SIZE_LIMIT=20000000
CMD [ "node", "server" ]
