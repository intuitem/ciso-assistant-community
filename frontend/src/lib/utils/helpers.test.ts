import { describe, it, test, expect } from 'vitest';

import {
	normalizeSearchString,
	getSearchTarget,
	roundScore,
	resolveResultTier,
	aggregateTieredResults
} from './helpers';

describe('normalizeSearchString', () => {
	it('lowercases and strips punctuation from Cyrillic text without emptying it', () => {
		expect(normalizeSearchString('Політика доступу')).toBe('політика доступу');
		expect(normalizeSearchString('Політика (v2.1)!')).toBe('політика v2 1');
	});

	it('still strips diacritics and punctuation from Latin text', () => {
		expect(normalizeSearchString('Café Policy!')).toBe('cafe policy');
	});
});

describe('getSearchTarget', () => {
	it('keeps Cyrillic option labels searchable instead of collapsing them to an empty string', () => {
		const target = getSearchTarget({ label: 'Політика доступу', value: 1 } as any);
		expect(target).not.toBe('');
		expect(target).toContain('політика');
	});

	it('lets a Cyrillic search term narrow down options the same way a Latin one does', () => {
		const options = [
			{ label: 'Політика доступу', value: 1 },
			{ label: 'Резервне копіювання', value: 2 }
		];
		const term = normalizeSearchString('доступу');
		const matches = options.filter((opt) => getSearchTarget(opt as any).includes(term));
		expect(matches.map((o) => o.value)).toEqual([1]);
	});
});

describe('resolveResultTier', () => {
	it('reads the tier a question states from what its choices can set', () => {
		expect(resolveResultTier(['compliant', 'non_compliant'])).toBe('compliant');
		expect(resolveResultTier(['partially_compliant', null])).toBe('partially_compliant');
		expect(resolveResultTier(['non_compliant', null])).toBe('blocking');
		expect(resolveResultTier([null, undefined])).toBe(null);
	});
});

describe('aggregateTieredResults', () => {
	const tier = (t: string | null, ...selected: string[]) => ({ tier: t, selected });

	it('awards a tier only when every statement of it holds', () => {
		expect(
			aggregateTieredResults([tier('compliant', 'compliant'), tier('compliant', 'compliant')])
		).toBe('compliant');
		expect(
			aggregateTieredResults([tier('compliant', 'compliant'), tier('compliant', 'non_compliant')])
		).toBe('non_compliant');
	});

	it('falls back to the partial tier when the top one breaks', () => {
		expect(
			aggregateTieredResults([
				tier('compliant', 'non_compliant'),
				tier('partially_compliant', 'partially_compliant')
			])
		).toBe('partially_compliant');
	});

	it('lets a triggered blocking statement deny every tier', () => {
		expect(
			aggregateTieredResults([tier('blocking', 'non_compliant'), tier('compliant', 'compliant')])
		).toBe('non_compliant');
		expect(aggregateTieredResults([tier('blocking'), tier('compliant', 'compliant')])).toBe(
			'compliant'
		);
	});

	it('treats an answer that affirms nothing as a failed tier', () => {
		expect(aggregateTieredResults([tier('compliant')])).toBe('non_compliant');
	});

	it('keeps not_applicable neutral', () => {
		expect(
			aggregateTieredResults([tier('compliant', 'compliant'), tier('compliant', 'not_applicable')])
		).toBe('compliant');
		expect(aggregateTieredResults([tier('compliant', 'not_applicable')])).toBe('not_applicable');
	});

	it('ignores not_applicable inside a mixed multiple-choice selection', () => {
		expect(
			aggregateTieredResults([
				tier('compliant', 'compliant', 'not_applicable'),
				tier('compliant', 'compliant')
			])
		).toBe('compliant');
		expect(
			aggregateTieredResults([
				tier('compliant', 'compliant', 'not_applicable'),
				tier('partially_compliant', 'not_applicable', 'partially_compliant')
			])
		).toBe('compliant');
	});

	it('ignores questions that state no tier', () => {
		expect(aggregateTieredResults([])).toBe(null);
		expect(aggregateTieredResults([tier(null, 'compliant')])).toBe(null);
	});
});

import {
	computeRequirementScoreAndResult,
	projectWeightedSum,
	questionScoreBounds
} from './helpers';

function weightedSumRa(weights: [number, number], maxima: [number, number] = [50, 50]) {
	const questions: Record<string, any> = {};
	(['q1', 'q2'] as const).forEach((key, i) => {
		questions[`urn:${key}`] = {
			type: 'unique_choice',
			weight: weights[i],
			choices: [
				{ urn: `urn:${key}:good`, add_score: maxima[i] },
				{ urn: `urn:${key}:bad`, add_score: 0 }
			]
		};
	});
	return {
		requirement: { questions },
		compliance_assessment: { min_score: 0, max_score: 100, score_calculation_method: 'sum' }
	};
}

describe('computeRequirementScoreAndResult with weighted SUM', () => {
	it('lets a heavy question count more while the top of the scale stays reachable', () => {
		const ra = weightedSumRa([3, 1]);
		const score = (q1: string, q2: string) =>
			computeRequirementScoreAndResult(ra, { 'urn:q1': `urn:q1:${q1}`, 'urn:q2': `urn:q2:${q2}` })
				.score;
		expect(score('good', 'bad')).toBe(75);
		expect(score('bad', 'good')).toBe(25);
		expect(score('good', 'good')).toBe(100);
		expect(score('bad', 'bad')).toBe(0);
	});

	it('does not saturate when the questions have uneven maxima', () => {
		const ra = weightedSumRa([3, 1], [70, 30]);
		const heavyAlone = computeRequirementScoreAndResult(ra, {
			'urn:q1': 'urn:q1:good',
			'urn:q2': 'urn:q2:bad'
		});
		expect(heavyAlone.score).toBe(87);
	});

	it('keeps the raw sum when every weight is 1', () => {
		const ra = weightedSumRa([1, 1]);
		expect(
			computeRequirementScoreAndResult(ra, { 'urn:q1': 'urn:q1:good', 'urn:q2': 'urn:q2:bad' })
				.score
		).toBe(50);
	});

	it('counts an unscored choice as zero in the reachable range', () => {
		const ra = weightedSumRa([3, 1]);
		ra.requirement.questions['urn:q2'].choices[1].add_score = null;
		const score = (q1: string, q2: string) =>
			computeRequirementScoreAndResult(ra, { 'urn:q1': `urn:q1:${q1}`, 'urn:q2': `urn:q2:${q2}` })
				.score;
		expect(score('good', 'bad')).toBe(75);
		expect(score('bad', 'bad')).toBe(0);
	});

	it('treats a negative weight as 0', () => {
		const ra = weightedSumRa([-2, 1]);
		expect(
			computeRequirementScoreAndResult(ra, { 'urn:q1': 'urn:q1:good', 'urn:q2': 'urn:q2:bad' })
				.score
		).toBe(0);
	});
});

describe('questionScoreBounds', () => {
	it('spans the single reachable score of a unique choice', () => {
		expect(questionScoreBounds([0, 50], false)).toEqual([0, 50]);
		expect(questionScoreBounds([-1, -2], false)).toEqual([-2, -1]);
	});

	it('adds up every positive and every negative score of a multiple choice', () => {
		expect(questionScoreBounds([10, 20, -5], true)).toEqual([-5, 30]);
		expect(questionScoreBounds([-1, -2], true)).toEqual([-3, -1]);
	});
});

describe('projectWeightedSum', () => {
	it('is the identity when the ranges coincide', () => {
		expect(projectWeightedSum(42, 0, 100, 0, 100)).toBe(42);
	});

	it('returns the raw total when nothing carries weight', () => {
		expect(projectWeightedSum(0, 0, 0, 0, 10)).toBe(0);
	});

	it('maps the whole range when 0 is out of reach', () => {
		// Choices 10/60 at weight 3 and 20/40 at weight 1: weighted [50, 220], unweighted [30, 100].
		expect(projectWeightedSum(50, 50, 220, 30, 100)).toBe(30);
		expect(projectWeightedSum(220, 50, 220, 30, 100)).toBe(100);
	});

	it('keeps a choice worth 0 neutral when a question can go negative', () => {
		// Weight 3 on [-10, 0], weight 1 on [0, 50]: weighted [-30, 50], unweighted [-10, 50].
		expect(projectWeightedSum(0, -30, 50, -10, 50)).toBe(0);
		expect(projectWeightedSum(-30, -30, 50, -10, 50)).toBe(-10);
		expect(projectWeightedSum(50, -30, 50, -10, 50)).toBe(50);
	});
});

describe('roundScore', () => {
	test('two decimals, half up, despite float noise', () => {
		expect(roundScore(68.335)).toBe(68.34);
		expect(roundScore(1.005)).toBe(1.01);
		expect(roundScore(2.9971)).toBe(3);
		expect(roundScore(41.125)).toBe(41.13);
		expect(roundScore(13 / 3)).toBe(4.33);
		expect(roundScore(1.234999999)).toBe(1.23);
		expect(roundScore(2.695)).toBe(2.7);
	});

	test('percentages keep one decimal, the nothing-scored sentinel stays', () => {
		expect(roundScore(66.66, 1)).toBe(66.7);
		expect(roundScore(-1)).toBe(-1);
	});
});

describe('computeRequirementScoreAndResult with tiered_all', () => {
	it('scores a complete answer whose selections state no result', () => {
		const statement = (key: string, onTrue: string) => ({
			type: 'unique_choice',
			choices: [
				{ urn: `urn:${key}:true`, compute_result: onTrue },
				{ urn: `urn:${key}:false`, compute_result: null }
			]
		});
		const ra = {
			requirement: {
				questions: {
					'urn:na': statement('na', 'non_compliant'),
					'urn:pa': statement('pa', 'partially_compliant')
				}
			},
			compliance_assessment: { framework: { result_aggregation: 'tiered_all' } }
		};
		expect(
			computeRequirementScoreAndResult(ra, { 'urn:na': 'urn:na:false', 'urn:pa': 'urn:pa:false' })
				.result
		).toBe('non_compliant');
	});
});
