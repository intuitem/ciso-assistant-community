import { describe, it, expect } from 'vitest';
import fc from 'fast-check';

import { truncateTitle } from './toc';
import { toCamelCase } from './locales';

// Property-based ("fuzz") tests: instead of fixed examples, fast-check feeds
// thousands of generated inputs and checks invariants hold for all of them.

describe('truncateTitle (property)', () => {
	it('never throws on arbitrary string + non-negative length', () => {
		fc.assert(
			fc.property(fc.string(), fc.nat(), (title, maxLength) => {
				truncateTitle(title, maxLength);
			})
		);
	});

	it('returns the input unchanged when it fits', () => {
		fc.assert(
			fc.property(fc.string(), fc.nat(), (title, maxLength) => {
				fc.pre(title.length <= maxLength);
				expect(truncateTitle(title, maxLength)).toBe(title);
			})
		);
	});

	it('truncates to a prefix of the original plus an ellipsis when too long', () => {
		fc.assert(
			fc.property(fc.string(), fc.nat(), (title, maxLength) => {
				fc.pre(title.length > maxLength);
				const result = truncateTitle(title, maxLength);
				expect(result.endsWith('...')).toBe(true);
				expect(result.slice(0, -3)).toBe(title.substring(0, maxLength));
			})
		);
	});
});

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
});
