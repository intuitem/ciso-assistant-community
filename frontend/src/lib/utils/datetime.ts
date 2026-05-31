import { page } from '$app/state';

export type DateFormatPreference =
	| 'auto'
	| 'iso'
	| 'ddmmyyyy'
	| 'mmddyyyy'
	| 'long_dmy'
	| 'long_mdy';

const DATE_FORMAT_PREFERENCES: DateFormatPreference[] = [
	'auto',
	'iso',
	'ddmmyyyy',
	'mmddyyyy',
	'long_dmy',
	'long_mdy'
];

function getDateFormatPreference(): DateFormatPreference {
	const pref = page?.data?.user?.preferences?.date_format;
	return DATE_FORMAT_PREFERENCES.includes(pref) ? pref : 'auto';
}

function pad(n: number): string {
	return n.toString().padStart(2, '0');
}

// Build a long-form date with a fixed component order while still localizing the
// month name (e.g. "mai" in French) — the order can't be forced through Intl
// options, so we read the localized parts and reassemble them ourselves.
function longDate(date: Date, locale: string, monthFirst: boolean): string {
	const parts = new Intl.DateTimeFormat(locale, {
		day: 'numeric',
		month: 'long',
		year: 'numeric'
	}).formatToParts(date);
	const find = (type: string) => parts.find((p) => p.type === type)?.value ?? '';
	const day = find('day');
	const month = find('month');
	const year = find('year');
	return monthFirst ? `${month} ${day}, ${year}` : `${day} ${month} ${year}`;
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
		case 'long_dmy':
			return longDate(date, locale, false);
		case 'long_mdy':
			return longDate(date, locale, true);
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
	const hasTime = isoString.includes('T');
	// A date-only ISO string (YYYY-MM-DD) is parsed as UTC midnight, which renders
	// the previous day in time zones west of UTC. Anchoring it with a local time
	// (no offset → parsed as local per the ES spec) preserves the calendar date.
	const date = new Date(hasTime ? isoString : `${isoString}T00:00:00`);
	return formatDate(date, hasTime, locale);
}

/**
 * Render a sample date string for a given preference, used in the settings UI.
 */
export function sampleDateForPreference(preference: DateFormatPreference, locale = 'en'): string {
	return formatDatePart(new Date(2026, 4, 31), preference, locale);
}
