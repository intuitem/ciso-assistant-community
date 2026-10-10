import { describe, expect, it } from 'vitest';
import {
	READ_ROW_DEFAULTS,
	aggregateRowsOf,
	applyActionDefaults,
	ensureAggregateRows,
	type ActionConfig
} from './read-config';

const READ_DEFAULTS = {
	model: 'applied_control',
	mode: 'list',
	filters: {},
	...READ_ROW_DEFAULTS
};

describe('applyActionDefaults', () => {
	it('fills what a list read lacks', () => {
		const config: ActionConfig = { type: 'read_objects' };
		applyActionDefaults(config, READ_DEFAULTS);
		expect(config).toMatchObject({ mode: 'list', order_by: '-created_at', limit: 25 });
	});

	it('never gives an aggregate read its row keys back', () => {
		// Publish refuses order_by and limit in aggregate mode, and the
		// Inspector hides them there: restoring them made the node unpublishable.
		const config: ActionConfig = {
			type: 'read_objects',
			model: 'applied_control',
			mode: 'aggregate',
			filters: {},
			aggregates: [{ fn: 'count' }]
		};
		applyActionDefaults(config, READ_DEFAULTS);
		for (const key of Object.keys(READ_ROW_DEFAULTS)) expect(config).not.toHaveProperty(key);
		expect(config.aggregates).toEqual([{ fn: 'count' }]);
	});

	it('keeps the row keys of other action types that share a name', () => {
		const config: ActionConfig = { type: 'http_request', mode: 'aggregate' };
		applyActionDefaults(config, { limit: 10 });
		expect(config.limit).toBe(10);
	});

	it('clones nested defaults so two nodes do not share them', () => {
		const a: ActionConfig = { type: 'read_objects' };
		const b: ActionConfig = { type: 'read_objects' };
		applyActionDefaults(a, READ_DEFAULTS);
		applyActionDefaults(b, READ_DEFAULTS);
		(a.include as string[]).push('progress');
		expect(b.include).toEqual([]);
	});
});

describe('aggregate rows', () => {
	it('reads a missing list as empty without writing it', () => {
		const config: ActionConfig = { type: 'read_objects', mode: 'aggregate' };
		expect(aggregateRowsOf(config)).toEqual([]);
		expect(config).not.toHaveProperty('aggregates');
	});

	it('creates the list on the first edit', () => {
		const config: ActionConfig = { mode: 'aggregate' };
		ensureAggregateRows(config).push({ fn: 'count' });
		expect(config.aggregates).toEqual([{ fn: 'count' }]);
		expect(aggregateRowsOf(config)).toBe(config.aggregates);
	});
});
