/**
 * Boolean display polarity configuration.
 *
 * Most boolean fields use "positive" polarity: true = good (green), false = neutral.
 * Some fields have "warning" polarity: true = needs attention (orange).
 * Some fields have "warning_when_false" polarity: false = needs attention (orange).
 *
 * Lookup order: "urlmodel:field" first, then "field" as global fallback.
 * Only fields with non-default polarity need to be listed here.
 */

export type BooleanPolarity = 'positive' | 'warning' | 'warning_when_false';

const POLARITY_MAP: Map<string, BooleanPolarity> = new Map([
	// Global defaults (apply unless overridden by a model-specific entry)
	['is_sensitive', 'warning'],
	['is_third_party', 'warning'],
	['keep_local_login', 'warning'],
	['has_mfa_enabled', 'warning_when_false'],
	['is_active', 'warning_when_false']

	// Model-specific overrides — use "urlmodel:field" format, e.g.:
	// ['contracts:is_active', 'warning'],
]);

export function getBooleanPolarity(fieldName: string, urlModel?: string): BooleanPolarity {
	if (urlModel) {
		const modelSpecific = POLARITY_MAP.get(`${urlModel}:${fieldName}`);
		if (modelSpecific) return modelSpecific;
	}
	return POLARITY_MAP.get(fieldName) ?? 'positive';
}

/**
 * Returns the icon class and color class for a boolean value given its field name.
 */
export function booleanDisplay(
	value: boolean,
	fieldName: string,
	urlModel?: string
): { icon: string; colorClass: string } {
	const polarity = getBooleanPolarity(fieldName, urlModel);

	if (value) {
		if (polarity === 'warning') {
			return { icon: 'fa-solid fa-circle', colorClass: 'text-orange-500' };
		}
		return { icon: 'fa-solid fa-circle', colorClass: 'text-green-500' };
	}

	// value is false
	if (polarity === 'warning_when_false') {
		return { icon: 'fa-solid fa-circle', colorClass: 'text-orange-500' };
	}
	return { icon: 'fa-regular fa-circle', colorClass: 'text-gray-400' };
}
