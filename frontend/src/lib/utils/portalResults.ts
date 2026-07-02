import { safeTranslate } from '$lib/utils/i18n';

// Compliance result breakdown shared by the framework tile and the snapshot drill-down.
export const RESULT_META = [
	{ key: 'compliant', label: 'compliant', color: '#86efac' },
	{ key: 'partially_compliant', label: 'partiallyCompliant', color: '#fde047' },
	{ key: 'non_compliant', label: 'nonCompliant', color: '#f87171' },
	{ key: 'not_applicable', label: 'notApplicable', color: '#000000' },
	{ key: 'not_assessed', label: 'notAssessed', color: '#d1d5db' }
] as const;

export const RESULT_BY_KEY: Record<string, { label: string; color: string }> = Object.fromEntries(
	RESULT_META.map((r) => [r.key, { label: r.label, color: r.color }])
);

export const donutValues = (summary: Record<string, any> | undefined) =>
	RESULT_META.map((r) => ({
		name: safeTranslate(r.label),
		value: summary?.[r.key] ?? 0,
		itemStyle: { color: r.color }
	})).filter((v) => v.value > 0);
