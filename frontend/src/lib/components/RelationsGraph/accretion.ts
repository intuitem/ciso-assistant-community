import type { GraphLink, Neighborhood } from './types';

/** Ego graph that grows by explicit expansion; positions are assigned on arrival and never recomputed. */

export interface LiveNode {
	id: string;
	urlModel: string;
	name: string;
	ref?: string;
	meta?: Record<string, string>;
	hop: number;
	parentId?: string;
	group?: string;
	angle: number;
	wedge: number;
	x: number;
	y: number;
	expanded: boolean;
	/** Whether the server says this node has relations of its own. */
	expandable?: boolean;
	navigable?: boolean;
	exhausted: boolean;
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

/** Model graph diameter is 3, so a fourth hop adds instances, not kinds. */
export const MAX_HOP = 3;

export const MAX_ARRIVALS = 25;

const RING_STEP = 300;
const ROOT_RADIUS = 300;
const MIN_ARC = 110;

export interface MergeOptions {
	fanCap: number;
	hidden?: Set<string>;
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
		node.expandable !== false
	);
}

/** Folds a fetched neighbourhood in under `parentId`, placing only new nodes. */
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

	// Walking back out of the arrival relation yields the hub's other children.
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
		// Only suppress the back-relation when it is actually a hub.
		const seen = key === backGroup && !backHoldsGrandparent ? onCanvas + 1 : onCanvas;
		const back = key === backGroup && total - seen > fanCap;
		return { key, fresh, onCanvas: seen, total, back, taken: 0 };
	});

	// Round-robin so every relation is represented; smallest first finishes what it can.
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
	// A "+1" placeholder costs the same slot as the node it hides.
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
			expandable: n.expandable,
			navigable: n.navigable,
			angle: p.angle,
			wedge: p.wedge,
			x: p.x,
			y: p.y,
			expanded: false,
			exhausted: hop >= MAX_HOP || n.expandable === false,
			frontier: hop >= MAX_HOP && n.expandable !== false
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

/** Children fan around the parent's bearing, one ring out; the fan does not inherit the parent's ring slot. */
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
	const radius = Math.max(Math.hypot(parent.x, parent.y) + RING_STEP, (count * MIN_ARC) / span);
	const start = parent.angle - span / 2 + step / 2;
	return Array.from({ length: count }, (_, i) => {
		const angle = start + i * step;
		return { angle, wedge: step, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
	});
}
