import {
	NODE_BY_ID,
	EDGES,
	neighborsOf,
	degreeOf,
	type NodeType,
	type UniverseNode
} from './universe';

export interface EgoNode {
	id: string;
	depth: number;
	type: NodeType;
	name: string;
	meta?: Record<string, string>;
	parentId?: string;
	/** Set on the synthetic "+N more" placeholders. */
	aggregate?: { parentId: string; type: NodeType; verb: string; count: number; key: string };
	x: number;
	y: number;
}

export interface EgoLink {
	source: string;
	target: string;
	verb: string;
	/** Depth of the deeper endpoint — used to fade far edges. */
	depth: number;
}

export interface EgoGraph {
	nodes: EgoNode[];
	links: EgoLink[];
	truncated: number;
}

export interface EgoOptions {
	rootId: string;
	depth: number;
	/** Max neighbours of the same (type, verb) kept per node before collapsing. */
	fanCap: number;
	hiddenTypes?: Set<NodeType>;
	/** Aggregate keys the user clicked open. */
	expanded?: Set<string>;
	/** width / height of the drawing area, so the rings fill a tall drawer. */
	aspect?: number;
}

const RADIUS = 400;
const RING = [0, 0.42, 0.82, 1];

export function buildEgoGraph({
	rootId,
	depth,
	fanCap,
	hiddenTypes = new Set(),
	expanded = new Set(),
	aspect = 1
}: EgoOptions): EgoGraph {
	const root = NODE_BY_ID.get(rootId);
	if (!root) return { nodes: [], links: [], truncated: 0 };

	const picked = new Map<string, EgoNode>();
	const aggregates: EgoNode[] = [];
	let truncated = 0;

	picked.set(rootId, { ...blank(root), depth: 0 });

	let frontier = [rootId];
	for (let d = 1; d <= depth; d++) {
		const next: string[] = [];
		for (const parentId of frontier) {
			const groups = new Map<string, { verb: string; type: NodeType; ids: string[] }>();
			for (const n of neighborsOf(parentId)) {
				if (picked.has(n.id)) continue;
				const node = NODE_BY_ID.get(n.id);
				if (!node || hiddenTypes.has(node.type)) continue;
				const key = `${parentId}|${node.type}|${n.verb}`;
				if (!groups.has(key)) groups.set(key, { verb: n.verb, type: node.type, ids: [] });
				const g = groups.get(key)!;
				if (!g.ids.includes(n.id)) g.ids.push(n.id);
			}

			for (const [key, g] of groups) {
				// Most-connected first: a hub neighbour is the one worth seeing.
				g.ids.sort((a, b) => degreeOf(b) - degreeOf(a));
				const open = expanded.has(key);
				const keep = open ? g.ids : g.ids.slice(0, fanCap);
				for (const id of keep) {
					if (picked.has(id)) continue;
					picked.set(id, { ...blank(NODE_BY_ID.get(id)!), depth: d, parentId });
					next.push(id);
				}
				const rest = g.ids.length - keep.length;
				if (rest > 0) {
					truncated += rest;
					aggregates.push({
						id: `agg:${key}`,
						depth: d,
						type: g.type,
						name: `+${rest}`,
						parentId,
						aggregate: { parentId, type: g.type, verb: g.verb, count: rest, key },
						x: 0,
						y: 0
					});
				}
			}
		}
		frontier = next;
	}

	for (const a of aggregates) picked.set(a.id, a);

	const links: EgoLink[] = [];
	for (const e of EDGES) {
		const s = picked.get(e.source);
		const t = picked.get(e.target);
		if (!s || !t) continue;
		links.push({ source: e.source, target: e.target, verb: e.verb, depth: Math.max(s.depth, t.depth) });
	}
	for (const a of aggregates) {
		links.push({ source: a.parentId!, target: a.id, verb: a.aggregate!.verb, depth: a.depth });
	}

	layout([...picked.values()], aspect);
	return { nodes: [...picked.values()], links, truncated };
}

function blank(n: UniverseNode): EgoNode {
	return { id: n.id, type: n.type, name: n.name, meta: n.meta, depth: 0, x: 0, y: 0 };
}

/**
 * Concentric rings, children fanned inside their parent's wedge. Deterministic on
 * purpose — a force layout of a 30-node ego network wobbles for two seconds and
 * lands somewhere different every time you open the same object.
 */
function layout(nodes: EgoNode[], aspect: number): void {
	const byDepth = new Map<number, EgoNode[]>();
	for (const n of nodes) {
		if (!byDepth.has(n.depth)) byDepth.set(n.depth, []);
		byDepth.get(n.depth)!.push(n);
	}

	const angle = new Map<string, number>();
	const wedge = new Map<string, number>();
	const root = byDepth.get(0)?.[0];
	if (!root) return;
	root.x = 0;
	root.y = 0;
	angle.set(root.id, 0);
	wedge.set(root.id, Math.PI * 2);

	// Circular rings leave a tall narrow drawer half empty, so the rings take the
	// shape of the box they are drawn in — clamped, because past ~2:1 it reads as a
	// squashed graph rather than a deliberate one.
	const ratio = Math.min(1.8, Math.max(0.55, aspect || 1));
	const sx = ratio >= 1 ? ratio : 1;
	const sy = ratio >= 1 ? 1 : 1 / ratio;

	const maxDepth = Math.max(...nodes.map((n) => n.depth));
	for (let d = 1; d <= maxDepth; d++) {
		const level = byDepth.get(d) ?? [];
		const r = RADIUS * (RING[Math.min(d, RING.length - 1)] ?? 1);

		if (d === 1) {
			// Group same-type neighbours side by side so the ring reads as sectors.
			level.sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));
			const step = (Math.PI * 2) / level.length;
			level.forEach((n, i) => {
				const a = i * step - Math.PI / 2;
				angle.set(n.id, a);
				wedge.set(n.id, step);
				n.x = Math.cos(a) * r * sx;
				n.y = Math.sin(a) * r * sy;
			});
			continue;
		}

		const byParent = new Map<string, EgoNode[]>();
		for (const n of level) {
			const p = n.parentId ?? root.id;
			if (!byParent.has(p)) byParent.set(p, []);
			byParent.get(p)!.push(n);
		}
		for (const [parentId, children] of byParent) {
			const base = angle.get(parentId) ?? 0;
			const span = (wedge.get(parentId) ?? Math.PI / 4) * 0.85;
			const step = span / children.length;
			children.sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));
			children.forEach((n, i) => {
				const a = base - span / 2 + step * (i + 0.5);
				angle.set(n.id, a);
				wedge.set(n.id, step);
				n.x = Math.cos(a) * r * sx;
				n.y = Math.sin(a) * r * sy;
			});
		}
	}
}
