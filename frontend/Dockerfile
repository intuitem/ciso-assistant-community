FROM node:18-alpine AS builder
WORKDIR /app

ARG PUBLIC_BACKEND_API_URL
ENV PUBLIC_BACKEND_API_URL=$PUBLIC_BACKEND_API_URL

COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build
RUN npm prune --production

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY package.json .
EXPOSE 3000
ENV NODE_ENV=development
CMD [ "node", "build" ]
