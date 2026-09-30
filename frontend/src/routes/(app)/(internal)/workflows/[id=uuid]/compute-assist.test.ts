import { describe, expect, it } from 'vitest';
import {
	applySuggestion,
	buildSuggestions,
	currentToken,
	recipes,
	type Scope
} from './compute-assist';

const scope: Scope = {
	variables: [
		{ key: 'likelihood', type: 'number' },
		{ key: 'impact', type: 'number' },
		{ key: 'label', type: 'string' }
	],
	referenceVariables: {
		likelihood: 4,
		impact: 4,
		today: '2026-09-30',
		payload: { severity: 'high' }
	},
	referenceNodes: [
		{
			key: 'fetch',
			label: 'Fetch controls',
			output: { count: 7, results: [{ score: 3, name: 'A' }] }
		}
	],
	upstreamNodes: [
		{ ref: 'fetch', label: 'Fetch controls', actionConfig: { type: 'read_objects' } },
		{ ref: 'each', label: 'Each', isLoop: true }
	]
};

describe('currentToken', () => {
	it('takes the identifier path ending at the cursor', () => {
		const value = '2 * nodes.fetch.cou';
		expect(currentToken(value, value.length)).toEqual({ start: 4, text: 'nodes.fetch.cou' });
	});

	it('is empty after an operator or a space', () => {
		expect(currentToken('a + ', 4)).toEqual({ start: 4, text: '' });
	});
});

describe('buildSuggestions', () => {
	it('offers nothing for an empty token', () => {
		expect(buildSuggestions('', scope)).toEqual([]);
	});

	it('completes variables, seeds, loop names and functions by prefix', () => {
		const texts = buildSuggestions('l', scope).map((s) => s.text);
		expect(texts).toContain('likelihood');
		expect(texts).toContain('label');
		expect(texts).not.toContain('impact');
		expect(buildSuggestions('to', scope)[0]).toMatchObject({ text: 'today', kind: 'seed' });
		expect(buildSuggestions('ite', scope)[0]).toMatchObject({ text: 'item', kind: 'loop' });
		expect(buildSuggestions('rou', scope)[0]).toMatchObject({
			text: 'round',
			insert: 'round()',
			cursorBack: 1
		});
	});

	it('shows the reference value next to a variable', () => {
		const [likelihood] = buildSuggestions('likelihood', scope);
		expect(likelihood.detail).toBe('number 4');
	});

	it('lists step refs after nodes. and output keys after nodes.<ref>.', () => {
		expect(buildSuggestions('nodes.', scope).map((s) => s.text)).toEqual(['fetch', 'each']);
		const keys = buildSuggestions('nodes.fetch.', scope);
		expect(keys.map((s) => s.text)).toEqual(['count', 'results']);
		expect(keys[0].insert).toBe('nodes.fetch.count');
	});

	it('offers list macros after a list and string methods after a string', () => {
		const macros = buildSuggestions('nodes.fetch.results.', scope);
		expect(macros[0]).toMatchObject({ text: 'map', insert: 'nodes.fetch.results.map(x, )' });
		const methods = buildSuggestions('payload.severity.st', scope);
		expect(methods.map((s) => s.text)).toEqual(['startsWith']);
	});

	it('caps the list', () => {
		expect(buildSuggestions('s', scope).length).toBeLessThanOrEqual(8);
	});
});

describe('applySuggestion', () => {
	it('replaces the token and puts the cursor inside parentheses', () => {
		const value = '1 + rou';
		const [round] = buildSuggestions('rou', scope);
		expect(applySuggestion(value, value.length, 4, round)).toEqual({
			value: '1 + round()',
			cursor: 10
		});
	});

	it('keeps text after the cursor', () => {
		const [impact] = buildSuggestions('imp', scope);
		expect(applySuggestion('imp * 2', 3, 0, impact)).toEqual({ value: 'impact * 2', cursor: 6 });
	});
});

describe('recipes', () => {
	it("uses the author's number variables and results step", () => {
		const byId = Object.fromEntries(recipes(scope).map((r) => [r.id, r.expression]));
		expect(byId.recipeScore).toBe('likelihood * impact');
		expect(byId.recipeRatio).toBe('round(double(likelihood) / double(impact) * 100.0, 1)');
		expect(byId.recipeWorst).toBe('max(nodes.fetch.results.map(r, r.score))');
		expect(byId.recipeCounter).toBe('likelihood + 1');
	});

	it('falls back to placeholder names on an empty scope', () => {
		const empty: Scope = {
			variables: [],
			referenceVariables: {},
			referenceNodes: [],
			upstreamNodes: []
		};
		const byId = Object.fromEntries(recipes(empty).map((r) => [r.id, r.expression]));
		expect(byId.recipeScore).toBe('likelihood * impact');
		expect(byId.recipeWorst).toBe('max(nodes.fetch.results.map(r, r.score))');
	});
});
