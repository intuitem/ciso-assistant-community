import { describe, it, expect } from 'vitest';

import {
	normalizeSearchString,
	getSearchTarget,
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

	it('ignores questions that state no tier', () => {
		expect(aggregateTieredResults([])).toBe(null);
		expect(aggregateTieredResults([tier(null, 'compliant')])).toBe(null);
	});
});
