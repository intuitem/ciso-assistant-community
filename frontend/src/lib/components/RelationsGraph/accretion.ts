import { RELATION_MAP } from './relations';
import type { GraphLink, Neighborhood } from './types';

/**
 * A graph that grows by accretion rather than by depth.
 *
 * Depth-as-a-dial was the wrong control: measured against real data, an applied
 * control reaches 4.9 objects at two hops and 147 at three, because the third hop
 * walks back out of every hub it just walked into. Here the reader expands one
 * node at a time, each expansion is one bounded request, and the graph only ever
 * holds what somebody asked to see.
 *
 * The invariant that makes it readable: **expansion never moves an existing
 * node.** Coordinates are assigned once, on arrival, inside the angular wedge the
 * parent owns. Recomputing the layout on every growth step would teleport
 * everything and destroy the reader's mental map.
 */

export interface LiveNode {
	id: string;
	urlModel: string;
	name: string;
	ref?: string;
	meta?: Record<string, string>;
	/** Hops from the record the drawer opened on. */
	hop: number;
	parentId?: string;
	/** Relation group this node arrived in, as keyed by its parent's payload. */
	group?: string;
	angle: number;
	wedge: number;
	x: number;
	y: number;
	expanded: boolean;
	/** Nothing more to show: a leaf, an unmapped model, or the hop limit. */
	exhausted: boolean;
	/** Sits at the hop limit — it has more, but not in this view. */
	frontier?: boolean;
	loading?: boolean;
	aggregate?: { parentId: string; group: string; count: number };
}

export interface LiveGraph {
	nodes: Map<string, LiveNode>;
	edges: Map<string, GraphLink>;
	notice: string;
}

export const NODE_BUDGET = 100;

/**
 * Measured, not guessed: with the back-relation rule on, the reachable set
 * saturates by here — an applied control gains 0.2 objects going from hop three
 * to four, a risk scenario gains 0.7 going from four to five. The model graph's
 * diameter is three, so a fourth hop cannot introduce a kind of object that is
 * not already on the canvas, only more instances of the same kinds.
 */
export const MAX_HOP = 3;

/**
 * Ceiling on what one click may add. A safety net, not a trimming policy — the
 * per-relation cap and the back-relation rule do the real work, and a graph that
 * hides what it could have shown does not earn its place.
 */
export const MAX_ARRIVALS = 25;

const RING_STEP = 300;
const ROOT_RADIUS = 300;
/** Minimum arc between siblings, in layout units, so a fan stays legible. */
const MIN_ARC = 110;

export interface MergeOptions {
	fanCap: number;
	hidden?: Set<string>;
	/** `${parentId}|${group}` keys the reader opened from a "+N". */
	opened?: Set<string>;
}

export function createGraph(root: {
	id: string;
	urlModel: string;
	name: string;
	ref?: string;
}): LiveGraph {
	const nodes = new Map<string, LiveNode>();
	nodes.set(root.id, {
		...root,
		hop: 0,
		angle: 0,
		wedge: Math.PI * 2,
		x: 0,
		y: 0,
		expanded: false,
		exhausted: false
	});
	return { nodes, edges: new Map(), notice: '' };
}

const edgeKey = (l: GraphLink) => `${l.source}|${l.target}|${l.verb}`;

export function setLoading(graph: LiveGraph, id: string, loading: boolean): LiveGraph {
	const node = graph.nodes.get(id);
	if (!node) return graph;
	const nodes = new Map(graph.nodes);
	nodes.set(id, { ...node, loading });
	return { ...graph, nodes, notice: loading ? '' : graph.notice };
}

/** True when expanding this node could show something. */
export function canExpand(node: LiveNode): boolean {
	return (
		!node.expanded &&
		!node.exhausted &&
		!node.aggregate &&
		node.hop < MAX_HOP &&
		node.urlModel in RELATION_MAP
	);
}

/**
 * Folds a fetched neighbourhood into the graph under `parentId`. Existing nodes
 * keep their identity and their coordinates; only new ones are placed.
 */
export function merge(
	graph: LiveGraph,
	parentId: string,
	payload: Neighborhood,
	{ fanCap, hidden = new Set(), opened = new Set() }: MergeOptions
): LiveGraph {
	const parent = graph.nodes.get(parentId);
	if (!parent) return graph;

	const nodes = new Map(graph.nodes);
	const edges = new Map(graph.edges);

	// The relation this node was reached through. Walking back out of it yields the
	// siblings of the node we came from — the two hundred other requirement
	// assessments of the audit we arrived via — whose only connection to the
	// subject is the hub in between.
	//
	// Identified by which group holds the node we came from, not by verb: the two
	// sides of a relation are named independently in the registry and need not
	// agree. That node is often absent, though, because the endpoint returns only
	// the first page of a large relation — precisely the hub case this rule exists
	// for. So fall back to matching on model, and only when it is unambiguous.
	const grandparent = parent.parentId ? graph.nodes.get(parent.parentId) : undefined;
	let backGroup = grandparent
		? payload.nodes.find((n) => n.id === grandparent.id)?.group
		: undefined;
	let backHoldsGrandparent = Boolean(backGroup);
	if (!backGroup && grandparent) {
		const candidates = [
			...new Set(
				payload.nodes.filter((n) => n.urlModel === grandparent.urlModel).map((n) => n.group)
			)
		];
		if (candidates.length === 1) backGroup = candidates[0];
	}

	const groups = new Map<string, typeof payload.nodes>();
	for (const n of payload.nodes) {
		if (n.id === parentId || hidden.has(n.urlModel)) continue;
		const key = n.group ?? n.urlModel;
		if (!groups.has(key)) groups.set(key, []);
		groups.get(key)!.push(n);
	}

	const queues = [...groups].map(([key, members]) => {
		const fresh = members.filter((m) => !nodes.has(m.id));
		const onCanvas = members.length - fresh.length;
		const total = payload.totals[key] ?? members.length;
		// Only worth suppressing the back-relation when it is actually a hub. A
		// requirement satisfied by three controls, reached from one of them, should
		// show the other two: they answer "what else covers this?", and they cost
		// less than the placeholder that would hide them.
		// The node we came from counts as already shown even when the page it would
		// have arrived on did not include it, or the placeholder overstates by one.
		const seen = key === backGroup && !backHoldsGrandparent ? onCanvas + 1 : onCanvas;
		const back = key === backGroup && total - seen > fanCap;
		return { key, fresh, onCanvas: seen, total, back, taken: 0 };
	});

	// Round-robin, so one crowded relation cannot crowd every other kind off the
	// canvas: you always see at least one of each thing this node is attached to.
	// Smallest first, so spare laps finish groups that can be finished. A group the
	// reader explicitly opened from a "+N" is exempt — they asked for it.
	for (const q of queues) if (opened.has(`${parentId}|${q.key}`)) q.taken = q.fresh.length;
	let allowance = MAX_ARRIVALS;
	const order = [...queues].sort((a, b) => a.fresh.length - b.fresh.length);
	let progressing = true;
	while (allowance > 0 && progressing) {
		progressing = false;
		for (const q of order) {
			if (allowance <= 0) break;
			if (q.back || opened.has(`${parentId}|${q.key}`)) continue;
			if (q.taken >= Math.min(fanCap, q.fresh.length)) continue;
			q.taken++;
			allowance--;
			progressing = true;
		}
	}
	// A "+1" placeholder occupies the same slot as the node it hides, so it is
	// never worth drawing. Take the straggler instead.
	for (const q of queues) {
		if (q.back && !opened.has(`${parentId}|${q.key}`)) continue;
		if (q.total - q.onCanvas - q.taken === 1 && q.fresh.length > q.taken) q.taken++;
	}

	const arrivals = queues.flatMap((q) =>
		q.fresh.slice(0, q.taken).map((n) => ({ ...n, group: q.key }))
	);
	const aggregates = queues
		.map((q) => ({ group: q.key, count: q.total - q.onCanvas - q.taken }))
		.filter((a) => a.count > 0);

	if (!arrivals.length && !aggregates.length) {
		nodes.set(parentId, { ...parent, expanded: true, exhausted: true, loading: false });
		for (const l of payload.links)
			if (nodes.has(l.source) && nodes.has(l.target)) edges.set(edgeKey(l), l);
		return { nodes, edges, notice: '' };
	}

	if (nodes.size + arrivals.length + aggregates.length > NODE_BUDGET) {
		return {
			...graph,
			nodes: new Map([...nodes, [parentId, { ...parent, loading: false }]]),
			notice: `That would push the graph past ${NODE_BUDGET} objects. Collapse something first.`
		};
	}

	const hop = parent.hop + 1;
	const positions = fanPositions(parent, arrivals.length + aggregates.length);

	arrivals.forEach((n, i) => {
		const p = positions[i];
		nodes.set(n.id, {
			id: n.id,
			urlModel: n.urlModel,
			name: n.name,
			ref: n.ref,
			meta: n.meta,
			hop,
			parentId,
			group: n.group,
			angle: p.angle,
			wedge: p.wedge,
			x: p.x,
			y: p.y,
			expanded: false,
			// A model with no entry in the registry has nothing we know how to show.
			exhausted: hop >= MAX_HOP || !(n.urlModel in RELATION_MAP),
			frontier: hop >= MAX_HOP && n.urlModel in RELATION_MAP
		});
	});

	aggregates.forEach((agg, j) => {
		const p = positions[arrivals.length + j];
		const id = `agg:${parentId}:${agg.group}`;
		const [, urlModel] = agg.group.split('|');
		nodes.set(id, {
			id,
			urlModel: urlModel ?? agg.group,
			name: `+${agg.count}`,
			hop,
			parentId,
			group: agg.group,
			angle: p.angle,
			wedge: p.wedge,
			x: p.x,
			y: p.y,
			expanded: false,
			exhausted: true,
			aggregate: { parentId, group: agg.group, count: agg.count }
		});
		const sample = groups.get(agg.group)?.[0];
		const inbound = sample
			? payload.links.some((l) => l.source === sample.id && l.target === parentId)
			: false;
		const verb =
			payload.links.find((l) => l.source === sample?.id || l.target === sample?.id)?.verb ?? '';
		edges.set(
			`${parentId}|${id}`,
			inbound ? { source: id, target: parentId, verb } : { source: parentId, target: id, verb }
		);
	});

	// Edges between nodes already on the canvas are free, and they are the most
	// interesting thing a graph can show: they close loops rather than grow it.
	for (const l of payload.links)
		if (nodes.has(l.source) && nodes.has(l.target)) edges.set(edgeKey(l), l);

	nodes.set(parentId, { ...parent, expanded: true, loading: false });
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
	if (!doomed.size) return { ...graph, notice: '' };

	const nodes = new Map<string, LiveNode>();
	for (const [id, n] of graph.nodes) {
		if (doomed.has(id)) continue;
		nodes.set(id, id === nodeId ? { ...n, expanded: false } : n);
	}
	const edges = new Map<string, GraphLink>();
	for (const [key, e] of graph.edges) {
		if (doomed.has(e.source) || doomed.has(e.target)) continue;
		edges.set(key, e);
	}
	return { nodes, edges, notice: '' };
}

/**
 * Places `count` children one ring further out, fanned around their parent's own
 * bearing so a branch reads as a branch.
 *
 * The fan deliberately does NOT inherit the parent's slice of the ring. A root
 * with nineteen neighbours owns 19° each, and six children crammed into 19° are a
 * smudge. Children live at a larger radius than the ring they grew from, so a
 * wide fan cannot collide with it — only with another branch expanded nearby,
 * which is rare and recoverable by collapsing.
 */
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
	const radius = Math.max(Math.hypot(parent.x, parent.y) + RING_STEP, (count * MIN_ARC) / span);
	const start = parent.angle - span / 2 + step / 2;
	return Array.from({ length: count }, (_, i) => {
		const angle = start + i * step;
		return { angle, wedge: step, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
	});
}
