# The image version should match the playwright version in the package.json
FROM mcr.microsoft.com/playwright:v1.45.1
WORKDIR /app

ENV PUBLIC_BACKEND_API_URL=foo

COPY ../package*.json .
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile
RUN npx playwright install --with-deps
COPY .. .
EXPOSE 9323
