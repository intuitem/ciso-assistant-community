// Mock for SvelteKit's `$app/env/public` under vitest.
// Unset variables are undefined, so constants.ts exercises its `??` fallbacks.
export const PUBLIC_HOOKS_URL: string | undefined = undefined;
export const PUBLIC_BACKEND_API_URL: string | undefined = undefined;
export const PUBLIC_DEFAULT_LANGUAGE: string | undefined = undefined;
export const PUBLIC_BACKEND_API_EXPOSED_URL: string | undefined = undefined;
