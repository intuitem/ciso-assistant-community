import { describe, expect, it } from 'vitest';
import { formatPercent } from './format';
import { compliancePercent } from '$lib/utils/compliance';

describe('formatPercent', () => {
	it('only shows 100% and 0% when exact', () => {
		expect(formatPercent(100)).toBe('100%');
		expect(formatPercent(99.5)).toBe('99%');
		expect(formatPercent(0)).toBe('0%');
		expect(formatPercent(0.25)).toBe('<1%');
		expect(formatPercent(42.4)).toBe('42%');
		expect(formatPercent(null)).toBe('—');
	});
});

describe('compliancePercent', () => {
	it('gives partial answers half credit over assessed requirements', () => {
		expect(compliancePercent(1, 2, 1)).toBe(50);
		expect(compliancePercent(0, 10, 0)).toBe(50);
		expect(compliancePercent(199, 0, 1)).toBeCloseTo(99.5);
		expect(compliancePercent(0, 0, 0)).toBeNull();
	});
});
