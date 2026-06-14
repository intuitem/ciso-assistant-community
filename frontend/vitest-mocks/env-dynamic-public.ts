// Mock for SvelteKit's `$env/dynamic/public` virtual module under vitest.
// constants.ts reads keys off `env` with Object.hasOwn and falls back to
// defaults, so an empty object exercises the fallback paths.
export const env: Record<string, string> = {};
