import { describe, expect, it } from 'vitest';
import { formatVariableValue, parseVariableValue } from './variable-values';

describe('formatVariableValue', () => {
	it('shows strings as they are and everything else as JSON', () => {
		expect(formatVariableValue('approvals@example.com')).toBe('approvals@example.com');
		expect(formatVariableValue(4)).toBe('4');
		expect(formatVariableValue(false)).toBe('false');
		expect(formatVariableValue({ a: 1 })).toBe('{"a":1}');
	});

	it('shows a json string as JSON so it parses back', () => {
		expect(formatVariableValue('hello', 'json')).toBe('"hello"');
		expect(parseVariableValue('json', formatVariableValue('hello', 'json'))).toEqual({
			ok: true,
			value: 'hello'
		});
		expect(formatVariableValue('hello', 'string')).toBe('hello');
	});

	it('shows no value as an empty field', () => {
		expect(formatVariableValue(null)).toBe('');
		expect(formatVariableValue(undefined)).toBe('');
	});
});

describe('parseVariableValue', () => {
	it('reads an empty field as no value for every type', () => {
		for (const type of ['string', 'number', 'boolean', 'date', 'json']) {
			expect(parseVariableValue(type, '  ')).toEqual({ ok: true, value: null });
		}
	});

	it('keeps strings verbatim', () => {
		expect(parseVariableValue('string', ' hi ')).toEqual({ ok: true, value: ' hi ' });
	});

	it('parses numbers and refuses text', () => {
		expect(parseVariableValue('number', '4')).toEqual({ ok: true, value: 4 });
		expect(parseVariableValue('number', '2.5')).toEqual({ ok: true, value: 2.5 });
		expect(parseVariableValue('number', 'abc')).toEqual({ ok: false });
		expect(parseVariableValue('number', '1.')).toEqual({ ok: true, value: 1 });
	});

	it('parses booleans only from true and false', () => {
		expect(parseVariableValue('boolean', 'true')).toEqual({ ok: true, value: true });
		expect(parseVariableValue('boolean', 'false')).toEqual({ ok: true, value: false });
		expect(parseVariableValue('boolean', 'yes')).toEqual({ ok: false });
	});

	it('accepts ISO dates only', () => {
		expect(parseVariableValue('date', '2026-10-02')).toEqual({ ok: true, value: '2026-10-02' });
		expect(parseVariableValue('date', '02/10/2026')).toEqual({ ok: false });
		expect(parseVariableValue('date', '2026-13-45')).toEqual({ ok: false });
		expect(parseVariableValue('date', '2014-02-30')).toEqual({ ok: false });
		expect(parseVariableValue('date', '2024-02-29')).toEqual({ ok: true, value: '2024-02-29' });
		expect(parseVariableValue('date', '2023-02-29')).toEqual({ ok: false });
		expect(parseVariableValue('date', '0001-01-01')).toEqual({ ok: true, value: '0001-01-01' });
	});

	it('parses JSON and rejects a half-typed value', () => {
		expect(parseVariableValue('json', '{"a": [1, 2]}')).toEqual({
			ok: true,
			value: { a: [1, 2] }
		});
		expect(parseVariableValue('json', '{"a": [1, ')).toEqual({ ok: false });
	});
});
