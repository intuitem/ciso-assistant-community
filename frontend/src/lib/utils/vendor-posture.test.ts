import { describe, expect, it } from 'vitest';
import { complianceShare, latestPerVendor, normalisedScore, postureOf } from './vendor-posture';
import type { ComplianceOverview } from './types';

const overview = (
	counts: Record<string, number>,
	score: Partial<ComplianceOverview['global_score']> = {},
	visibility = { show_result: true, show_score: true }
): ComplianceOverview => ({
	donut: {
		values: Object.entries(counts).map(([name, value]) => ({
			name,
			localName: name,
			value,
			itemStyle: { color: '#000' }
		}))
	},
	global_score: {
		maturity_score: -1,
		min_score: 0,
		max_score: 100,
		total_max_score: 100,
		score_calculation_method: 'avg',
		...score
	},
	...visibility
});

describe('complianceShare', () => {
	it('counts partial as half and leaves not applicable out', () => {
		// (4 + 2/2) / (10 - 2) = 62.5
		expect(
			complianceShare(
				overview({ compliant: 4, partially_compliant: 2, non_compliant: 2, not_applicable: 2 })
			)
		).toBe(63);
	});

	it('counts unanswered requirements against the vendor', () => {
		expect(complianceShare(overview({ compliant: 5, not_assessed: 5 }))).toBe(50);
	});

	it('has no value when nothing is applicable', () => {
		expect(complianceShare(overview({ not_applicable: 3 }))).toBeNull();
	});
});

describe('normalisedScore', () => {
	it('maps the score onto its own scale', () => {
		expect(
			normalisedScore(overview({}, { maturity_score: 3, min_score: 1, total_max_score: 5 }))
		).toBe(50);
	});

	it('starts a sum at zero', () => {
		expect(
			normalisedScore(
				overview(
					{},
					{ maturity_score: 30, min_score: 1, total_max_score: 40, score_calculation_method: 'sum' }
				)
			)
		).toBe(75);
	});

	it('has no value for an unscored audit', () => {
		expect(normalisedScore(overview({}))).toBeNull();
	});
});

describe('postureOf', () => {
	it('never falls back from one metric to the other', () => {
		const audit = overview({ compliant: 1 });
		expect(postureOf(audit, 'compliance')).toEqual({ value: 100 });
		expect(postureOf(audit, 'score')).toEqual({ missing: 'noScore' });
	});

	it('respects the audit visibility', () => {
		const audit = overview({ compliant: 1 }, {}, { show_result: false, show_score: false });
		expect(postureOf(audit, 'compliance')).toEqual({ missing: 'hidden' });
	});

	it('treats a vendor without questionnaire as not assessed', () => {
		expect(postureOf(null, 'compliance')).toEqual({ missing: 'notAssessed' });
	});
});

describe('latestPerVendor', () => {
	const row = (entity_id: string, updated_at: string, audit = 'a') => ({
		entity_id,
		updated_at,
		compliance_assessment_id: audit
	});

	it('keeps the most recent assessment with a questionnaire', () => {
		const rows = [
			row('v1', '2026-01-01T10:00:00'),
			row('v1', '2026-03-01T10:00:00'),
			row('v1', '2026-05-01T10:00:00', '#'),
			row('v2', '2026-02-01T10:00:00', '#')
		];
		expect(latestPerVendor(rows)).toEqual([rows[1], rows[3]]);
	});
});
