export function formatDateOrDateTime(isoString: string, locale = 'en-US'): string {
	const hasTime = isoString.includes('T');

	const date = new Date(isoString);

	if (hasTime) {
		return date.toLocaleString(locale);
	} else {
		return date.toLocaleDateString(locale);
	}
}
