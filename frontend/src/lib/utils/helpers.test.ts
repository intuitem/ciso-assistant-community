import { describe, it, test, expect } from 'vitest';

import { normalizeSearchString, getSearchTarget, roundScore } from './helpers';

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

describe('roundScore', () => {
	test('two decimals, half up, despite float noise', () => {
		expect(roundScore(68.335)).toBe(68.34);
		expect(roundScore(1.005)).toBe(1.01);
		expect(roundScore(2.9971)).toBe(3);
		expect(roundScore(41.125)).toBe(41.13);
		expect(roundScore(13 / 3)).toBe(4.33);
	});

	test('percentages keep one decimal, the nothing-scored sentinel stays', () => {
		expect(roundScore(66.66, 1)).toBe(66.7);
		expect(roundScore(-1)).toBe(-1);
	});
});
