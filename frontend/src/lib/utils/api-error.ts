import { safeTranslate } from '#lib/utils/i18n.js';

/**
 * Turn a DRF error body into a human message.
 * Errors arrive as {detail}, {error: code}, or a field map
 * ({packager: ["packagerTooLong"]}); surface the first one, translating codes.
 */
export function apiErrorMessage(err: any): string {
	if (err?.detail) return err.detail;
	if (err?.error) return safeTranslate(err.error);
	for (const v of Object.values(err ?? {})) {
		const code = Array.isArray(v) ? v[0] : v;
		if (typeof code === 'string') return safeTranslate(code);
	}
	return JSON.stringify(err);
}
