import { describe, expect, it } from 'vitest';
import { tidyLayout, visibleList } from './layout';
import type { RingNode } from './types';

const node = (id: string, children: RingNode[] = []): RingNode => ({
	id,
	label: id,
	branch: null,
	children
});

// root ─ a ─ a1, a2
//      └ b ─ b1
const tree = node('root', [node('a', [node('a1'), node('a2')]), node('b', [node('b1')])]);

describe('visibleList', () => {
	it('lists visible nodes in pre-order with depth', () => {
		expect(visibleList(tree, new Set()).map((r) => `${r.node.id}:${r.depth}`)).toEqual([
			'root:0',
			'a:1',
			'a1:2',
			'a2:2',
			'b:1',
			'b1:2'
		]);
	});

	it('hides the children of collapsed nodes', () => {
		expect(visibleList(tree, new Set(['a'])).map((r) => r.node.id)).toEqual([
			'root',
			'a',
			'b',
			'b1'
		]);
	});

	it('keeps only the given ids below the root', () => {
		expect(
			visibleList(tree, new Set(), new Set(['root', 'b', 'b1'])).map((r) => r.node.id)
		).toEqual(['root', 'b', 'b1']);
	});
});

describe('tidyLayout', () => {
	const { nodes, edges, byId } = tidyLayout(tree, new Set(), undefined, 200, 100);

	it('places depth on x and siblings on y', () => {
		expect(byId.get('root')!.x).toBe(0);
		expect(byId.get('a')!.x).toBe(200);
		expect(byId.get('a1')!.x).toBe(400);
		expect(byId.get('a2')!.y - byId.get('a1')!.y).toBe(100);
	});

	it('centres a parent on its children', () => {
		const a = byId.get('a')!;
		expect(a.y).toBeCloseTo((byId.get('a1')!.y + byId.get('a2')!.y) / 2);
	});

	it('keeps nodes of the same depth apart', () => {
		const leaves = nodes
			.filter((p) => p.depth === 2)
			.map((p) => p.y)
			.sort((x, y) => x - y);
		for (let i = 1; i < leaves.length; i++)
			expect(leaves[i] - leaves[i - 1]).toBeGreaterThanOrEqual(100);
	});

	it('returns nodes in pre-order and one edge per non-root node', () => {
		expect(nodes.map((p) => p.node.id)).toEqual(['root', 'a', 'a1', 'a2', 'b', 'b1']);
		expect(edges).toHaveLength(5);
	});
});
