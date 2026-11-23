import { describe, expect, it } from 'vitest';
import { listViewFields } from './table';
import { FIELD_KEYS, FILTER_KEYS } from './param-keys';

const views = Object.values(listViewFields);

describe('param-keys mirrors listViewFields (regenerate on failure)', () => {
	it('FIELD_KEYS', () => {
		const keys = new Set(views.flatMap((v) => ('body' in v && v.body ? v.body : [])));
		expect([...FIELD_KEYS].sort()).toEqual([...keys].sort());
	});

	it('FILTER_KEYS', () => {
		const keys = new Set(
			views.flatMap((v) => ('filters' in v && v.filters ? Object.keys(v.filters) : []))
		);
		expect([...FILTER_KEYS].sort()).toEqual([...keys].sort());
	});
});
