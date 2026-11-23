/**
 * Rounds a percentage towards the middle so that 100% and 0% are only shown when
 * exact: 99.5 reads "99%", 0.3 reads "<1%".
 */
export function formatPercent(v: number | null | undefined): string {
	if (v === null || v === undefined) return '—';
	if (v > 0 && v < 1) return '<1%';
	if (v > 99 && v < 100) return '99%';
	return `${Math.round(v)}%`;
}
