import { describe, it, expect } from 'vitest';
import fc from 'fast-check';

import { toCamelCase } from './locales';

// Property-based ("fuzz") tests: instead of fixed examples, fast-check feeds
// thousands of generated inputs and checks invariants hold for all of them.

describe('toCamelCase (property)', () => {
	it('never throws on arbitrary string', () => {
		fc.assert(
			fc.property(fc.string(), (s) => {
				toCamelCase(s);
			})
		);
	});

	it('is a no-op on non-string input', () => {
		fc.assert(
			fc.property(fc.oneof(fc.integer(), fc.boolean(), fc.constant(null)), (value) => {
				// @ts-expect-error intentionally passing non-string to exercise the guard
				expect(toCamelCase(value)).toBe(value);
			})
		);
	});

	it('leaves separator-free input unchanged except for a lowercased first character', () => {
		fc.assert(
			fc.property(fc.stringMatching(/^[A-Za-z][A-Za-z0-9]*$/), (s) => {
				const expected = s.charAt(0).toLowerCase() + s.slice(1);
				expect(toCamelCase(s)).toBe(expected);
			})
		);
	});

	it('strips parentheses instead of leaving them embedded in the key', () => {
		expect(toCamelCase('Real time (continuous)')).toBe('realTimeContinuous');
		expect(toCamelCase('ICT operation management (including maintenance)')).toBe(
			'iCTOperationManagementIncludingMaintenance'
		);
		expect(toCamelCase('Software licencing (excluding SaaS)')).toBe(
			'softwareLicencingExcludingSaaS'
		);
		expect(toCamelCase('foo(bar)')).toBe('fooBar');
	});
});
