import * as m from '$paraglide/messages.js';
import { toCamelCase } from '$lib/utils/locales';

/**
 * Safe translate function that returns the key if the translation is not found.
 * @param key The key to translate.
 * @param params The parameters to pass to the translation function.
 * @param options The options to pass to the translation function.
 */
export function safeTranslate(key: string, params = {}, options = {}): string {
	const toCamekey = toCamelCase(key);
	if (Object.hasOwn(m, toCamekey)) {
		return m[toCamekey](params, options);
	}
	return key;
}
