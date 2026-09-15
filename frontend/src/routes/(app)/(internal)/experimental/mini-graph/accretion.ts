import { NODE_BY_ID, neighborsOf, degreeOf, type NodeType } from './universe';

/** Prototype of the accretion model; the shipped one is $lib/components/RelationsGraph. */

export interface LiveNode {
	id: string;
	type: NodeType;
	name: string;
	meta?: Record<string, string>;
	/** Hops from the node the panel opened on. */
	hop: number;
	parentId?: string;
	/** Angular slice this node may place its own children in. */
	angle: number;
	wedge: number;
	x: number;
	y: number;
	expanded: boolean;
	/** True once we know it has nothing more to give. */
	exhausted: boolean;
	/** Sits at the hop limit: it has more, but not in this view. */
	frontier?: boolean;
	/** How this node was reached, so expanding it does not walk straight back out
	 *  through the same relation and drag the whole hub along. */
	arrivalType?: NodeType;
	arrivalVerb?: string;
	aggregate?: { parentId: string; group: string; count: number };
}

export interface LiveEdge {
	source: string;
	target: string;
	verb: string;
}

export interface LiveGraph {
	nodes: Map<string, LiveNode>;
	edges: Map<string, LiveEdge>;
	/** Set when the last expansion was refused. */
	notice: string;
}

export const NODE_BUDGET = 100;
export const MAX_HOP = 3;
export const MAX_ARRIVALS = 25;
const RING_STEP = 300;
const ROOT_RADIUS = 300;
/** Minimum arc between siblings, in layout units, so a fan stays legible. */
const MIN_ARC = 110;

export function createGraph(rootId: string): LiveGraph {
	const node = NODE_BY_ID.get(rootId);
	const nodes = new Map<string, LiveNode>();
	if (node) {
		nodes.set(rootId, {
			id: rootId,
			type: node.type,
			name: node.name,
			meta: node.meta,
			hop: 0,
			angle: 0,
			wedge: Math.PI * 2,
			x: 0,
			y: 0,
			expanded: false,
			exhausted: false
		});
	}
	return { nodes, edges: new Map(), notice: '' };
}

const edgeKey = (a: string, b: string, verb: string) =>
	a < b ? `${a}|${b}|${verb}` : `${b}|${a}|${verb}`;

export interface ExpandOptions {
	fanCap: number;
	hidden?: Set<NodeType>;
	/** Aggregate groups the user opened, so "+N" can be popped in place. */
	opened?: Set<string>;
}

/**
 * Returns a NEW graph with `nodeId`'s neighbours attached. Existing nodes keep
 * their identity and, critically, their coordinates.
 */
export function expand(
	graph: LiveGraph,
	nodeId: string,
	{ fanCap, hidden = new Set(), opened = new Set() }: ExpandOptions
): LiveGraph {
	const parent = graph.nodes.get(nodeId);
	if (!parent) return graph;
	if (parent.hop >= MAX_HOP) {
		return {
			...graph,
			notice: `${MAX_HOP} hops is as far as this view goes. Open that object to explore from there.`
		};
	}

	const nodes = new Map(graph.nodes);
	const edges = new Map(graph.edges);

	// Group by relation, exactly as the ring does, so a fan reads as sectors.
	const groups = new Map<string, { verb: string; type: NodeType; ids: string[] }>();
	for (const n of neighborsOf(nodeId)) {
		const target = NODE_BY_ID.get(n.id);
		if (!target || hidden.has(target.type)) continue;
		const key = `${nodeId}|${target.type}|${n.verb}`;
		if (!groups.has(key)) groups.set(key, { verb: n.verb, type: target.type, ids: [] });
		const g = groups.get(key)!;
		if (!g.ids.includes(n.id)) g.ids.push(n.id);
	}

	// Edges to nodes already on screen are free: they close loops rather than grow
	// the graph, and they are the most interesting thing a graph can show you.
	for (const n of neighborsOf(nodeId)) {
		if (!nodes.has(n.id)) continue;
		const key = edgeKey(nodeId, n.id, n.verb);
		if (!edges.has(key)) {
			edges.set(
				key,
				n.inbound
					? { source: n.id, target: nodeId, verb: n.verb }
					: { source: nodeId, target: n.id, verb: n.verb }
			);
		}
	}

	const queues = [...groups]
		.map(([key, g]) => {
			// Most-connected first: a hub neighbour is the one worth seeing.
			const fresh = g.ids.filter((id) => !nodes.has(id)).sort((a, b) => degreeOf(b) - degreeOf(a));
			const arrived = g.type === parent.arrivalType && g.verb === parent.arrivalVerb;
			return {
				key,
				verb: g.verb,
				type: g.type,
				fresh,
				back: arrived && fresh.length > fanCap,
				taken: 0
			};
		})
		.filter((q) => q.fresh.length);

	let allowance = MAX_ARRIVALS;
	for (const q of queues) {
		if (!opened.has(q.key)) continue;
		q.taken = q.fresh.length;
	}
	// Smallest relations first, so the spare laps go to groups that can actually be
	// finished instead of leaving a "+1" behind a nearly-complete one.
	const order = [...queues].sort((a, b) => a.fresh.length - b.fresh.length);
	let progressing = true;
	while (allowance > 0 && progressing) {
		progressing = false;
		for (const q of order) {
			if (allowance <= 0) break;
			if (opened.has(q.key)) continue;
			if (q.back) continue;
			if (q.taken >= Math.min(fanCap, q.fresh.length)) continue;
			q.taken++;
			allowance--;
			progressing = true;
		}
	}

	// A "+1" placeholder occupies the same slot on the canvas as the node it hides,
	// so it is never worth drawing. Take the straggler instead.
	for (const q of queues) {
		if (q.back && !opened.has(q.key)) continue;
		if (q.fresh.length - q.taken === 1) q.taken++;
	}

	const arrivals: { id: string; verb: string; inbound: boolean; group: string }[] = [];
	const aggregates: { group: string; type: NodeType; verb: string; count: number }[] = [];
	for (const q of queues) {
		for (const id of q.fresh.slice(0, q.taken)) {
			const inbound = neighborsOf(nodeId).find((n) => n.id === id)?.inbound ?? false;
			arrivals.push({ id, verb: q.verb, inbound, group: q.key });
		}
		const rest = q.fresh.length - q.taken;
		if (rest > 0) aggregates.push({ group: q.key, type: q.type, verb: q.verb, count: rest });
	}

	if (!arrivals.length && !aggregates.length) {
		const next = new Map(nodes);
		next.set(nodeId, { ...parent, expanded: true, exhausted: true });
		return { nodes: next, edges, notice: '' };
	}

	if (nodes.size + arrivals.length + aggregates.length > NODE_BUDGET) {
		return {
			...graph,
			notice: `That would push the graph past ${NODE_BUDGET} nodes. Collapse something first.`
		};
	}

	const slots = arrivals.length + aggregates.length;
	const positions = fanPositions(parent, slots);

	arrivals.forEach((a, i) => {
		const src = NODE_BY_ID.get(a.id)!;
		const p = positions[i];
		nodes.set(a.id, {
			id: a.id,
			type: src.type,
			name: src.name,
			meta: src.meta,
			hop: parent.hop + 1,
			parentId: nodeId,
			angle: p.angle,
			wedge: p.wedge,
			x: p.x,
			y: p.y,
			expanded: false,
			exhausted: parent.hop + 1 >= MAX_HOP,
			frontier: parent.hop + 1 >= MAX_HOP,
			arrivalType: parent.type,
			arrivalVerb: a.verb
		});
		const key = edgeKey(nodeId, a.id, a.verb);
		edges.set(
			key,
			a.inbound
				? { source: a.id, target: nodeId, verb: a.verb }
				: { source: nodeId, target: a.id, verb: a.verb }
		);
	});

	aggregates.forEach((agg, j) => {
		const i = arrivals.length + j;
		const p = positions[i];
		const id = `agg:${agg.group}`;
		nodes.set(id, {
			id,
			type: agg.type,
			name: `+${agg.count}`,
			hop: parent.hop + 1,
			parentId: nodeId,
			angle: p.angle,
			wedge: p.wedge,
			x: p.x,
			y: p.y,
			expanded: false,
			exhausted: true,
			aggregate: { parentId: nodeId, group: agg.group, count: agg.count }
		});
		edges.set(edgeKey(nodeId, id, agg.verb), { source: nodeId, target: id, verb: agg.verb });
	});

	nodes.set(nodeId, { ...parent, expanded: true });
	return { nodes, edges, notice: '' };
}

/** Drops everything that arrived because of `nodeId`, recursively. */
export function collapse(graph: LiveGraph, nodeId: string): LiveGraph {
	const doomed = new Set<string>();
	const walk = (id: string) => {
		for (const n of graph.nodes.values()) {
			if (n.parentId === id && !doomed.has(n.id)) {
				doomed.add(n.id);
				walk(n.id);
			}
		}
	};
	walk(nodeId);
	if (!doomed.size) return graph;

	const nodes = new Map<string, LiveNode>();
	for (const [id, n] of graph.nodes) {
		if (doomed.has(id)) continue;
		nodes.set(id, id === nodeId ? { ...n, expanded: false } : n);
	}
	const edges = new Map<string, LiveEdge>();
	for (const [key, e] of graph.edges) {
		if (doomed.has(e.source) || doomed.has(e.target)) continue;
		edges.set(key, e);
	}
	return { nodes, edges, notice: '' };
}

/** Pops a "+N" placeholder into the nodes it stands for. */
export function openAggregate(graph: LiveGraph, aggId: string, options: ExpandOptions): LiveGraph {
	const agg = graph.nodes.get(aggId);
	if (!agg?.aggregate) return graph;
	const nodes = new Map(graph.nodes);
	nodes.delete(aggId);
	const edges = new Map(graph.edges);
	for (const [key, e] of edges) if (e.source === aggId || e.target === aggId) edges.delete(key);
	const parent = nodes.get(agg.aggregate.parentId);
	if (parent) nodes.set(parent.id, { ...parent, expanded: false });
	return expand({ nodes, edges, notice: '' }, agg.aggregate.parentId, {
		...options,
		opened: new Set([...(options.opened ?? []), agg.aggregate.group])
	});
}

/** Children fan around the parent's bearing, one ring out. */
function fanPositions(parent: LiveNode, count: number) {
	if (parent.hop === 0) {
		const step = (Math.PI * 2) / count;
		const radius = Math.max(ROOT_RADIUS, (count * MIN_ARC) / (Math.PI * 2));
		return Array.from({ length: count }, (_, i) => {
			const angle = -Math.PI / 2 + i * step;
			return { angle, wedge: step, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
		});
	}

	const span = Math.max(Math.PI / 4, 1.9 * 0.72 ** (parent.hop - 1));
	const step = span / count;
	// Push the ring out far enough that siblings are MIN_ARC apart along the arc,
	// rather than letting a wide fan of many children collapse into a smudge.
	const radius = Math.max(distance(parent) + RING_STEP, (count * MIN_ARC) / span);
	const start = parent.angle - span / 2 + step / 2;

	return Array.from({ length: count }, (_, i) => {
		const angle = start + i * step;
		return { angle, wedge: step, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
	});
}

function distance(n: LiveNode): number {
	return Math.hypot(n.x, n.y);
}

/** Radius of the whole graph, for the viewport fit. */
export function extent(graph: LiveGraph): number {
	let max = ROOT_RADIUS;
	for (const n of graph.nodes.values()) max = Math.max(max, distance(n));
	return max;
}
