import { page } from '$app/state';

export type DateFormatPreference = 'auto' | 'iso' | 'ddmmyyyy' | 'mmddyyyy' | 'long';

function getDateFormatPreference(): DateFormatPreference {
	const pref = page?.data?.user?.preferences?.date_format;
	return pref === 'iso' || pref === 'ddmmyyyy' || pref === 'mmddyyyy' || pref === 'long'
		? pref
		: 'auto';
}

function pad(n: number): string {
	return n.toString().padStart(2, '0');
}

function formatDatePart(date: Date, preference: DateFormatPreference, locale: string): string {
	switch (preference) {
		case 'iso':
			return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
		case 'ddmmyyyy':
			return date.toLocaleDateString('en-GB', {
				day: '2-digit',
				month: '2-digit',
				year: 'numeric'
			});
		case 'mmddyyyy':
			return date.toLocaleDateString('en-US', {
				day: '2-digit',
				month: '2-digit',
				year: 'numeric'
			});
		case 'long':
			return date.toLocaleDateString(locale, {
				day: 'numeric',
				month: 'long',
				year: 'numeric'
			});
		default:
			return date.toLocaleDateString(locale);
	}
}

/**
 * Format a Date for display, honoring the current user's date_format preference
 * (falling back to the locale-driven default when set to 'auto').
 * Set withTime to also append a localized time component.
 */
export function formatDate(date: Date, withTime = false, locale = 'en'): string {
	if (!(date instanceof Date) || isNaN(date.getTime())) {
		return '';
	}
	const preference = getDateFormatPreference();

	if (preference === 'auto') {
		return withTime ? date.toLocaleString(locale) : date.toLocaleDateString(locale);
	}

	const datePart = formatDatePart(date, preference, locale);
	return withTime ? `${datePart} ${date.toLocaleTimeString(locale)}` : datePart;
}

/**
 * Format an ISO date or datetime string for display. The presence of a time
 * component is inferred from the ISO string (the "T" separator).
 */
export function formatDateOrDateTime(isoString: string, locale = 'en'): string {
	if (typeof isoString !== 'string') {
		return isoString;
	}
	return formatDate(new Date(isoString), isoString.includes('T'), locale);
}

/**
 * Render a sample date string for a given preference, used in the settings UI.
 */
export function sampleDateForPreference(preference: DateFormatPreference, locale = 'en'): string {
	return formatDatePart(new Date(2026, 4, 31), preference, locale);
}
