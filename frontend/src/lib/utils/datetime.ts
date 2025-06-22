export function formatDateOrDateTime(isoString: string, locale = 'en-US'): string {
	if (typeof isoString !== 'string') {
		return isoString;
	}
	const hasTime = isoString.includes('T');

	const date = new Date(isoString);

	if (hasTime) {
		return date.toLocaleString(locale);
	} else {
		return date.toLocaleDateString(locale);
	}
}
