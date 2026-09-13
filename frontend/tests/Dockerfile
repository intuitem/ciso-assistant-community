# The image version should match the playwright version in the package.json
FROM mcr.microsoft.com/playwright:v1.45.1
WORKDIR /app

ENV PUBLIC_BACKEND_API_URL=foo

COPY ../package*.json .
# Install the exact pnpm version pinned by packageManager so a newer global
# pnpm doesn't delegate through its own version manager.
RUN npm install -g "pnpm@$(node -p "require('./package.json').packageManager.split('@')[1]")"
RUN pnpm install --frozen-lockfile
RUN npx playwright install --with-deps
COPY .. .
EXPOSE 9323
