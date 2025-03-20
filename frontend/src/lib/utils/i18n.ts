import * as m from '$paraglide/messages.js';
import { toCamelCase } from '$lib/utils/locales';

/**
 * Unafe translate function that doesn't return anything if the key if the translation is not found.
 * @param key The key to translate.
 * @param params The parameters to pass to the translation function.
 * @param options The options to pass to the translation function.
 */
export function unsafeTranslate(key: string, params = {}, options = {}): string | undefined {
	// Check if the key exists in the messages object
	if (Object.hasOwn(m, toCamelCase(key))) {
		return m[toCamelCase(key)](params, options);
	}

	// Check for keys in the format 'prefix:suffix'
	const prefixSuffixMatch = key.match('^([^:]+):([^:]+)$');
	if (prefixSuffixMatch) {
		const [, prefix, suffix] = prefixSuffixMatch;
		const translatedPrefix = Object.hasOwn(m, toCamelCase(prefix)) ? m[toCamelCase(prefix)](params, options) : prefix;
		return `${translatedPrefix}:${suffix}`;
	}

	// Check for keys in the format 'source->target'
	const sourceTargetMatch = key.match('^([^->]+)->([^->]+)$');
	if (sourceTargetMatch) {
		const [, source, target] = sourceTargetMatch;
		const translatedSource = Object.hasOwn(m, toCamelCase(source)) ? m[toCamelCase(source)](params, options) : source;
		const translatedTarget = Object.hasOwn(m, toCamelCase(target)) ? m[toCamelCase(target)](params, options) : target;
		return `${translatedSource}->${translatedTarget}`;
	}

	// Check for camelCase keys
	if (Object.hasOwn(m, toCamelCase(key))) {
		return m[toCamelCase(key)](params, options);
	}

	// Handle boolean keys
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
