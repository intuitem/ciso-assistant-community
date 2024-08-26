import { env } from "$env/dynamic/private";

export function loadFeatureFlags() {
  return {
    whiteLabel: env.FF_WHITE_LABEL === "true",
  };
}
