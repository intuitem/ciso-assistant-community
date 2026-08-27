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
