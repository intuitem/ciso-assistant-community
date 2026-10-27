import { defineEnvVars } from '@sveltejs/kit/env';

// Unset stays undefined so callers' `??` defaults keep applying
const optional = (input: string | undefined) => input;

export const variables = defineEnvVars({
	PUBLIC_HOOKS_URL: { public: true, schema: optional },
	PUBLIC_BACKEND_API_URL: { public: true, schema: optional },
	PUBLIC_DEFAULT_LANGUAGE: { public: true, schema: optional },
	PUBLIC_BACKEND_API_EXPOSED_URL: { public: true, schema: optional },
	// Read by the enterprise overlay only
	PUBLIC_LICENSE_EXPIRATION_NOTIFY_DAYS: { public: true, schema: optional },
	PUBLIC_LICENSE_EXPIRATION_MESSAGE: { public: true, schema: optional },
	LOG_FORMAT: { schema: optional },
	LOG_LEVEL: { schema: optional }
});
