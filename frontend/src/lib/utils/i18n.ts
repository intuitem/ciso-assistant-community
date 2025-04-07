import { m } from '$paraglide/messages';
import { toCamelCase } from '$lib/utils/locales';

/**
 * Unafe translate function that doesn't return anything if the key if the translation is not found.
 * @param key The key to translate.
 * @param params The parameters to pass to the translation function.
 * @param options The options to pass to the translation function.
 */
export function unsafeTranslate(key: string, params = {}, options = {}): string | undefined {
	try {
		if (Object.hasOwn(m, key) && typeof m[key] === 'function') {
			return m[key](params, options);
		}
		if (typeof key === 'string' && key) {
			let res = key.match('^([^:]+):([^:]+)$');
			if (res) {
				return (
					(Object.hasOwn(m, res[1]) && typeof m[res[1]] === 'function'
						? m[res[1]](params, options)
						: res[1]) +
					':' +
					res[2]
				);
			}
		}
		if (Object.hasOwn(m, toCamelCase(key)) && typeof m[toCamelCase(key)] === 'function') {
			return m[toCamelCase(key)](params, options);
		}
		if (typeof key === 'boolean') {
			return key ? '✅' : '❌';
		}
		if (typeof key === 'string' && key.includes('->')) {
			const parts = key.split('->');
			if (parts.length === 2) {
				const [from, to] = parts;
				const translatedFrom = m[toCamelCase(from)] ? m[toCamelCase(from)](params, options) : from;
				const translatedTo = m[toCamelCase(to)] ? m[toCamelCase(to)](params, options) : to;
				return translatedFrom + '->' + translatedTo;
			}
		}
	} catch (e) {
		console.error(`Error translating key "${key}"`, e);
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
