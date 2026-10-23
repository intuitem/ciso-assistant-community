import type { ComplianceOverview } from '$lib/utils/types';

export type PostureMetric = 'compliance' | 'score';

/** Why a vendor has no value for the chosen metric. */
export type Missing = 'notAssessed' | 'noScore' | 'hidden';

/**
 * Compliance share of an audit, in %: (compliant + ½ partial) over every
 * applicable requirement. Unanswered requirements count against the vendor,
 * so nobody reaches 100 % without answering everything.
 */
export function complianceShare(overview: ComplianceOverview): number | null {
	const count = (name: string) =>
		overview.donut.values.find((slice) => slice.name === name)?.value ?? 0;
	const total = overview.donut.values.reduce((sum, slice) => sum + slice.value, 0);
	const applicable = total - count('not_applicable');
	if (applicable <= 0) return null;
	return Math.round(((count('compliant') + count('partially_compliant') / 2) / applicable) * 100);
}

/** Audit maturity score normalised to 0-100 on its own scale (same bounds as the card). */
export function normalisedScore(overview: ComplianceOverview): number | null {
	const score = overview.global_score;
	if (!score || score.maturity_score == null || score.maturity_score < 0) return null;
	const floor = score.score_calculation_method === 'sum' ? 0 : (score.min_score ?? 0);
	const ceiling = score.total_max_score ?? 100;
	if (ceiling <= floor) return null;
	const value = ((score.maturity_score - floor) / (ceiling - floor)) * 100;
	return Math.round(Math.min(100, Math.max(0, value)));
}

export function postureOf(
	overview: ComplianceOverview | null | undefined,
	metric: PostureMetric
): { value: number } | { missing: Missing } {
	if (!overview) return { missing: 'notAssessed' };
	if (metric === 'score') {
		if (!overview.show_score) return { missing: 'hidden' };
		const value = normalisedScore(overview);
		return value == null ? { missing: 'noScore' } : { value };
	}
	if (!overview.show_result) return { missing: 'hidden' };
	const value = complianceShare(overview);
	return value == null ? { missing: 'notAssessed' } : { value };
}

/**
 * One assessment per vendor: the most recently updated one that has a
 * questionnaire, else the most recent of all.
 */
export function latestPerVendor<
	T extends { entity_id: string; updated_at: string; compliance_assessment_id: string }
>(assessments: T[]): T[] {
	const rank = (a: T) => [a.compliance_assessment_id !== '#' ? 1 : 0, a.updated_at] as const;
	const best = new Map<string, T>();
	for (const assessment of assessments) {
		const current = best.get(assessment.entity_id);
		if (!current) {
			best.set(assessment.entity_id, assessment);
			continue;
		}
		const [hasA, dateA] = rank(assessment);
		const [hasB, dateB] = rank(current);
		if (hasA > hasB || (hasA === hasB && dateA > dateB)) best.set(assessment.entity_id, assessment);
	}
	return [...best.values()];
}
