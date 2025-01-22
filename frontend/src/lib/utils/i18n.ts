import * as m from '$paraglide/messages.js';
import { toCamelCase } from '$lib/utils/locales';

/**
 * Unafe translate function that doesn't return anything if the key if the translation is not found.
 * @param key The key to translate.
 * @param params The parameters to pass to the translation function.
 * @param options The options to pass to the translation function.
 */
export function unsafeTranslate(key: string, params = {}, options = {}): string | undefined {
	if (Object.hasOwn(m, key)) {
		return m[key](params, options);
	}
	if (typeof key === 'string' && key) {
		let res = key.match('^([^:]+):([^:]+)$');
		if (res) {
			return (Object.hasOwn(m, res[1]) ? m[res[1]](params, options) : res[1]) + ':' + res[2];
		}
	}
	if (Object.hasOwn(m, toCamelCase(key))) {
		return m[toCamelCase(key)](params, options);
	}
	if (typeof key === 'boolean') {
		return key ? '✅' : '❌';
	}
}

/**
 * Safe translate function that returns the key if the translation is not found.
 * @param key The key to translate.
 * @param params The parameters to pass to the translation function.
 * @param options The options to pass to the translation function.
 */
export function safeTranslate(key: string, params = {}, options = {}): string {
	return unsafeTranslate(key, params, options) || key;
}
