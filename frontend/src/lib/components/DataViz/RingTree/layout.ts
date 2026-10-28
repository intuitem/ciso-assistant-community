import { hierarchy, tree } from 'd3-hierarchy';
import type { RingNode } from './types';

export interface Placed {
	node: RingNode;
	depth: number;
	x: number;
	y: number;
}

/** Children shown under `n`: none when collapsed, only those in `only` when given. */
export function visibleChildren(n: RingNode, collapsed: Set<string>, only?: Set<string>) {
	if (collapsed.has(n.id)) return [];
	return only ? n.children.filter((c) => only.has(c.id)) : n.children;
}

/** Visible nodes in pre-order, for list renderings. */
export function visibleList(root: RingNode, collapsed: Set<string>, only?: Set<string>) {
	const out: { node: RingNode; depth: number }[] = [];
	const walk = (n: RingNode, depth: number) => {
		out.push({ node: n, depth });
		for (const c of visibleChildren(n, collapsed, only)) walk(c, depth + 1);
	};
	walk(root, 0);
	return out;
}

/** Left-to-right Reingold–Tilford layout of the visible tree. */
export function tidyLayout(
	root: RingNode,
	collapsed: Set<string>,
	only: Set<string> | undefined,
	colW: number,
	rowH: number
) {
	const h = hierarchy(root, (n) => visibleChildren(n, collapsed, only));
	tree<RingNode>()
		.nodeSize([rowH, colW])
		.separation((a, b) => (a.parent === b.parent ? 1 : 1.2))(h);

	const nodes: Placed[] = [];
	const byId = new Map<string, Placed>();
	h.eachBefore((d) => {
		const p = { node: d.data, depth: d.depth, x: d.y!, y: d.x! };
		nodes.push(p);
		byId.set(d.data.id, p);
	});
	const edges = h.links().map((l) => [byId.get(l.source.data.id)!, byId.get(l.target.data.id)!]);
	let y0 = Infinity;
	let y1 = -Infinity;
	let x1 = 0;
	for (const p of nodes) {
		y0 = Math.min(y0, p.y);
		y1 = Math.max(y1, p.y);
		x1 = Math.max(x1, p.x);
	}
	return { nodes, edges: edges as [Placed, Placed][], byId, bounds: { x0: 0, y0, x1, y1 } };
}
