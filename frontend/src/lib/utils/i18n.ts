import * as m from '$paraglide/messages.js';

/**
 * Safe translate function that returns the key if the translation is not found.
 * @param key The key to translate.
 * @param params The parameters to pass to the translation function.
 * @param options The options to pass to the translation function.
 */
export function safeTranslate(key: string, params = {}, options = {}): string {
	if (Object.hasOwn(m, key)) {
		return m[key](params, options);
	}
	return key;
}
