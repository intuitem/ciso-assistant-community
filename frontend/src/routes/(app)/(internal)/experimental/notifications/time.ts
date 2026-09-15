/** Fixed "now" so the mock reads the same on every render. */
export const NOW = new Date('2026-09-14T09:30:00Z').getTime();

export function relTime(iso: string): string {
	const mins = Math.round((NOW - new Date(iso).getTime()) / 60000);
	if (mins < 1) return 'just now';
	if (mins < 60) return `${mins}m ago`;
	const hours = Math.round(mins / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.round(hours / 24);
	if (days < 30) return `${days}d ago`;
	return `${Math.round(days / 30)}mo ago`;
}

export function shortDate(iso: string): string {
	return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}
