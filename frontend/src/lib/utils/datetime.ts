export function formatDateOrDateTime(isoString: string, locale = 'en'): string {
	if (typeof isoString !== 'string') {
		return isoString;
	}

	const date = new Date(isoString);
	const hasTime = isoString.includes('T');

	if (hasTime) {
		return date.toLocaleString(locale);
	} else {
		return date.toLocaleDateString(locale);
	}
}
