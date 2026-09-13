import type { GraphLink, GraphNode, Neighborhood } from './types';

export interface PlacedNode extends GraphNode {
	depth: 0 | 1;
	/** Set on the synthetic "+N" placeholders. */
	aggregate?: { group: string; count: number };
	x: number;
	y: number;
}

export interface PlacedGraph {
	nodes: PlacedNode[];
	links: (GraphLink & { toRoot: boolean })[];
	collapsed: number;
}

const RADIUS = 400;

export interface PlaceOptions {
	fanCap: number;
	hidden?: Set<string>;
	expanded?: Set<string>;
	/** width / height of the drawing area, so the ring fills a tall drawer. */
	aspect?: number;
}

export function placeNeighborhood(
	data: Neighborhood,
	{ fanCap, hidden = new Set(), expanded = new Set(), aspect = 1 }: PlaceOptions
): PlacedGraph {
	const root: PlacedNode = { ...data.root, depth: 0, x: 0, y: 0 };

	const groups = new Map<string, GraphNode[]>();
	for (const n of data.nodes) {
		if (n.id === root.id) continue;
		if (hidden.has(n.urlModel)) continue;
		const key = n.group ?? n.urlModel;
		if (!groups.has(key)) groups.set(key, []);
		groups.get(key)!.push(n);
	}

	const kept: PlacedNode[] = [];
	const aggregates: PlacedNode[] = [];
	let collapsed = 0;

	for (const [key, members] of [...groups].sort((a, b) => a[0].localeCompare(b[0]))) {
		const total = data.totals[key] ?? members.length;
		const open = expanded.has(key);
		const shown = open ? members : members.slice(0, fanCap);
		for (const n of shown) kept.push({ ...n, depth: 1, x: 0, y: 0 });
		// Anything the server did not send counts as collapsed too, otherwise a
		// control cited by 300 requirements silently looks like it has 25.
		const rest = total - shown.length;
		if (rest > 0) {
			collapsed += rest;
			aggregates.push({
				id: `agg:${key}`,
				urlModel: members[0].urlModel,
				name: `+${rest}`,
				group: key,
				aggregate: { group: key, count: rest },
				depth: 1,
				x: 0,
				y: 0
			});
		}
	}

	// Each group shares one verb and one direction; remember them so the "+N"
	// placeholder can be wired the same way as the members it stands for.
	const groupOf = new Map<string, string>();
	for (const n of data.nodes) groupOf.set(n.id, n.group ?? n.urlModel);
	const groupEdge = new Map<string, { verb: string; inbound: boolean }>();
	for (const l of data.links) {
		const other = l.source === root.id ? l.target : l.source;
		const key = groupOf.get(other);
		if (key && !groupEdge.has(key)) {
			groupEdge.set(key, { verb: l.verb, inbound: l.target === root.id });
		}
	}

	const nodes = [root, ...kept, ...aggregates];
	const present = new Set(nodes.map((n) => n.id));
	const links = data.links
		.filter((l) => present.has(l.source) && present.has(l.target))
		.map((l) => ({ ...l, toRoot: l.target === root.id }));

	for (const a of aggregates) {
		const edge = groupEdge.get(a.aggregate!.group);
		const inbound = edge?.inbound ?? false;
		links.push({
			source: inbound ? a.id : root.id,
			target: inbound ? root.id : a.id,
			verb: edge?.verb ?? '',
			toRoot: inbound
		});
	}

	layout(nodes, aspect);
	return { nodes, links, collapsed };
}

/**
 * One ring, grouped by relation so the circle reads as sectors. Deterministic:
 * a force layout of 20 nodes wobbles for two seconds and lands somewhere new
 * every time the same record is opened.
 */
function layout(nodes: PlacedNode[], aspect: number): void {
	const ring = nodes.filter((n) => n.depth === 1);
	if (!ring.length) return;

	// Circular rings leave a tall narrow drawer half empty, so the ring takes the
	// shape of the box — clamped, because past ~2:1 it reads as squashed.
	const ratio = Math.min(1.8, Math.max(0.55, aspect || 1));
	const sx = ratio >= 1 ? ratio : 1;
	const sy = ratio >= 1 ? 1 : 1 / ratio;

	ring.sort(
		(a, b) =>
			(a.group ?? a.urlModel).localeCompare(b.group ?? b.urlModel) || a.name.localeCompare(b.name)
	);
	const step = (Math.PI * 2) / ring.length;
	ring.forEach((n, i) => {
		const angle = i * step - Math.PI / 2;
		n.x = Math.cos(angle) * RADIUS * sx;
		n.y = Math.sin(angle) * RADIUS * sy;
	});
}
