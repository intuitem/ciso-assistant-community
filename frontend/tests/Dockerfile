# The image version should match the playwright version in the package.json
FROM mcr.microsoft.com/playwright:v1.40.1
WORKDIR /app

ARG PUBLIC_BACKEND_API_URL
ENV PUBLIC_BACKEND_API_URL=$PUBLIC_BACKEND_API_URL

COPY ../package*.json .
RUN npm ci
RUN npx playwright install --with-deps
COPY .. .
EXPOSE 9323