import { describe, it, expect } from 'vitest';

import { normalizeSearchString, getSearchTarget } from './helpers';

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

	it('falls back to the raw total on a zero-width range', () => {
		expect(projectWeightedSum(7, 5, 5, 0, 10)).toBe(7);
	});
});
