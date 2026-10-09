import { describe, expect, it } from 'vitest';
import {
	aliasOf,
	datasetNameProblem,
	formulaKind,
	inputReferences,
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
