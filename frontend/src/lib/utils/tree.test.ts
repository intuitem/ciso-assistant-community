import { describe, expect, it } from 'vitest';
import { nestedIds, subtreeIds, type TreeRow } from '$lib/utils/tree';

const rows: TreeRow[] = [
	{ id: 'root', parent_folder: null },
	{ id: 'a', parent_folder: { id: 'root' } },
	{ id: 'a1', parent_folder: { id: 'a' } },
	{ id: 'a11', parent_folder: { id: 'a1' } },
	{ id: 'b', parent_folder: { id: 'root' } }
];

describe('subtreeIds', () => {
	it('keeps a root and everything below it', () => {
		expect(subtreeIds(rows, ['a'])).toEqual(new Set(['a', 'a1', 'a11']));
	});

	it('leaves siblings and ancestors out', () => {
		expect(subtreeIds(rows, ['a1'])).toEqual(new Set(['a1', 'a11']));
	});

	it('merges the subtrees of several roots', () => {
		expect(subtreeIds(rows, ['a1', 'b'])).toEqual(new Set(['a1', 'a11', 'b']));
	});

	it('returns the roots alone when nothing hangs from them', () => {
		expect(subtreeIds(rows, ['a11'])).toEqual(new Set(['a11']));
	});

	it('terminates on a cycle', () => {
		const looped: TreeRow[] = [
			{ id: 'x', parent_folder: { id: 'y' } },
			{ id: 'y', parent_folder: { id: 'x' } }
		];
		expect(subtreeIds(looped, ['x'])).toEqual(new Set(['x', 'y']));
	});

	it('accepts numeric ids', () => {
		const numeric: TreeRow[] = [{ id: 1 }, { id: 2, parent_folder: { id: 1 } }];
		expect(subtreeIds(numeric, ['1'])).toEqual(new Set(['1', '2']));
	});
});

describe('nestedIds', () => {
	it('keeps the ids filed below another selected id, at any depth', () => {
		expect(nestedIds(rows, ['a', 'a1', 'a11', 'b'])).toEqual(new Set(['a1', 'a11']));
	});

	it('is empty when no selected id sits below another', () => {
		expect(nestedIds(rows, ['a1', 'b'])).toEqual(new Set());
	});

	it('terminates on a cycle', () => {
		const looped: TreeRow[] = [
			{ id: 'x', parent_folder: { id: 'y' } },
			{ id: 'y', parent_folder: { id: 'x' } }
		];
		expect(nestedIds(looped, ['x'])).toEqual(new Set());
	});
});
