import { describe, expect, it } from 'vitest';
import {
	aliasOf,
	datasetNameProblem,
	formulaKind,
	formulaScope,
	inputReferences,
	sampleMoment,
	sanitizeDatasetName
} from './derived-metrics';

describe('datasetNameProblem', () => {
	it('accepts a fresh identifier', () => {
		expect(datasetNameProblem('active', ['controls'])).toBeNull();
	});

	it('refuses a name another dataset has', () => {
		// Datasets are keyed by name: a duplicate replaced the other one on save.
		expect(datasetNameProblem('controls', ['controls', 'late'])).toBe('taken');
	});

	it('refuses an empty name', () => {
		expect(datasetNameProblem('', ['controls'])).toBe('required');
	});

	it('refuses what the backend refuses', () => {
		expect(datasetNameProblem('1st', [])).toBe('invalid');
		expect(datasetNameProblem('metrics', [])).toBe('invalid');
		expect(datasetNameProblem('previous', [])).toBe('invalid');
	});
});

describe('sanitizeDatasetName', () => {
	it('keeps identifier characters only', () => {
		expect(sanitizeDatasetName('late controls!')).toBe('late_controls_');
	});
});

describe('aliasOf', () => {
	it('mirrors the backend default aliases', () => {
		expect(aliasOf({ fn: 'count' })).toBe('count');
		expect(aliasOf({ fn: 'count', group_by: 'status' })).toBe('by_status');
		expect(aliasOf({ fn: 'avg', field: 'priority' })).toBe('avg_priority');
		expect(aliasOf({ fn: 'max', field: 'eta', group_by: 'status' })).toBe('max_eta_by_status');
		expect(aliasOf({ fn: 'count', as: 'total' })).toBe('total');
	});
});

describe('metric formulas', () => {
	it('offer the inputs and previous to the expression', () => {
		expect(
			inputReferences([
				{ key: 'clicks', definition: 'a', combine: 'one' },
				{ key: 'trained', definition: 'b', combine: 'sum' }
			])
		).toEqual(['clicks', 'trained', 'previous']);
		expect(inputReferences(null)).toEqual([]);
		expect(inputReferences([{ key: '' }])).toEqual([]);
	});

	it('read other metrics only when inputs are set', () => {
		expect(formulaKind([{ key: 'x', definition: 'a', combine: 'one' }])).toBe('metrics');
		expect(formulaKind([])).toBe('objects');
		expect(formulaKind(null)).toBe('objects');
	});

	it('name inputs with the dataset rules', () => {
		expect(datasetNameProblem('now', [])).toBe('invalid');
		expect(datasetNameProblem('clicks', ['clicks'])).toBe('taken');
	});
});

describe('sampleMoment', () => {
	it('plots a period sample at its period start, not at its UTC end', () => {
		// November, stamped at its last instant: shown as December 1st in Paris.
		expect(
			sampleMoment({
				timestamp: '2025-11-30T23:59:59.999999Z',
				period_start: '2025-11-01T00:00:00Z'
			})
		).toBe('2025-11-01T00:00:00Z');
	});

	it('plots any other sample at its timestamp', () => {
		expect(sampleMoment({ timestamp: '2026-10-05T09:00:00Z', period_start: null })).toBe(
			'2026-10-05T09:00:00Z'
		);
		expect(sampleMoment({ timestamp: '2026-10-05T09:00:00Z' })).toBe('2026-10-05T09:00:00Z');
	});
});

describe('formulaScope', () => {
	it('offers datasets with their aliases after a dot, previous and metrics', () => {
		const scope = formulaScope(
			'objects',
			{
				controls: { model: 'applied_control', aggregates: [{ fn: 'count' }] },
				active: { model: 'applied_control', aggregates: [{ fn: 'count', group_by: 'status' }] }
			},
			null
		);
		expect(scope.variables.map((v) => v.key)).toEqual([
			'controls',
			'active',
			'metrics',
			'previous'
		]);
		expect(Object.keys(scope.referenceVariables)).toEqual(['controls', 'active']);
		expect(Object.keys(scope.referenceVariables.controls as object)).toEqual(['count']);
		expect(Object.keys(scope.referenceVariables.active as object)).toEqual(['by_status']);
	});

	it('shows what the last preview answered', () => {
		const scope = formulaScope(
			'objects',
			{ controls: { model: 'applied_control', aggregates: [{ fn: 'count' }] } },
			null,
			{ datasets: { controls: { count: 34 } } }
		);
		expect(scope.referenceVariables).toEqual({ controls: { count: 34 } });
	});

	it('offers the inputs of a metric formula with their latest period values', () => {
		const scope = formulaScope(
			'metrics',
			null,
			[
				{ key: 'clicks', definition: 'a', combine: 'sum' },
				{ key: 'headcount', definition: 'b', combine: 'sum' }
			],
			{
				periods: [
					{ inputs: { clicks: 50, headcount: 900 } },
					{ inputs: { clicks: 30, headcount: 950 } }
				]
			}
		);
		expect(scope.variables.map((v) => v.key)).toEqual(['clicks', 'headcount', 'previous']);
		expect(scope.referenceVariables).toEqual({ clicks: 30, headcount: 950 });
	});
});
