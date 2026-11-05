import dagre from '@dagrejs/dagre';
import type { Edge, Node } from '@xyflow/svelte';

type XY = { x: number; y: number };

const DEFAULT_SIZE = { width: 180, height: 56 };
const COMPONENT_GAP = 100;
const BAND_GAP = 140;
const GRID_GAP_X = 40;
const GRID_GAP_Y = 36;

const sizeOf = (node: Node) => ({
	width: node.measured?.width ?? DEFAULT_SIZE.width,
	height: node.measured?.height ?? DEFAULT_SIZE.height
});

function components(nodes: Node[], edges: Edge[]): string[][] {
	const parent = new Map(nodes.map((n) => [n.id, n.id]));
	const find = (id: string): string => {
		let root = id;
		while (parent.get(root) !== root) root = parent.get(root)!;
		parent.set(id, root);
		return root;
	};
	for (const e of edges) {
		if (!parent.has(e.source) || !parent.has(e.target)) continue;
		parent.set(find(e.source), find(e.target));
	}
	const groups = new Map<string, string[]>();
	for (const n of nodes) {
		const root = find(n.id);
		groups.set(root, [...(groups.get(root) ?? []), n.id]);
	}
	return [...groups.values()];
}

function layoutComponent(ids: string[], byId: Map<string, Node>, edges: Edge[]) {
	const graph = new dagre.graphlib.Graph();
	graph.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 40, edgesep: 20 });
	graph.setDefaultEdgeLabel(() => ({}));
	const members = new Set(ids);
	for (const id of ids) graph.setNode(id, sizeOf(byId.get(id)!));
	for (const e of edges) {
		if (members.has(e.source) && members.has(e.target)) graph.setEdge(e.source, e.target);
	}
	dagre.layout(graph);

	const local = new Map<string, XY>();
	let minX = Infinity;
	let minY = Infinity;
	let maxX = -Infinity;
	let maxY = -Infinity;
	for (const id of ids) {
		const placed = graph.node(id);
		const { width, height } = sizeOf(byId.get(id)!);
		const x = placed.x - width / 2;
		const y = placed.y - height / 2;
		local.set(id, { x, y });
		minX = Math.min(minX, x);
		minY = Math.min(minY, y);
		maxX = Math.max(maxX, x + width);
		maxY = Math.max(maxY, y + height);
	}
	for (const [id, p] of local) local.set(id, { x: p.x - minX, y: p.y - minY });
	return { local, width: maxX - minX, height: maxY - minY };
}

export function computeLayout(nodes: Node[], edges: Edge[]): Map<string, XY> {
	const byId = new Map(nodes.map((n) => [n.id, n]));
	const groups = components(nodes, edges);
	const linked = groups.filter((g) => g.length > 1).sort((a, b) => b.length - a.length);
	const isolated = groups
		.filter((g) => g.length === 1)
		.map((g) => byId.get(g[0])!)
		.sort((a, b) => Number(a.type === 'ghost') - Number(b.type === 'ghost'));

	const positions = new Map<string, XY>();
	let cursorX = 0;
	let bandHeight = 0;
	for (const group of linked) {
		const { local, width, height } = layoutComponent(group, byId, edges);
		for (const [id, p] of local) {
			positions.set(id, { x: Math.round(cursorX + p.x), y: Math.round(p.y) });
		}
		cursorX += width + COMPONENT_GAP;
		bandHeight = Math.max(bandHeight, height);
	}

	if (isolated.length) {
		const cellW = Math.max(...isolated.map((n) => sizeOf(n).width)) + GRID_GAP_X;
		const cellH = Math.max(...isolated.map((n) => sizeOf(n).height)) + GRID_GAP_Y;
		const bandWidth = Math.max(cursorX - COMPONENT_GAP, cellW * 4);
		const cols = Math.max(
			4,
			Math.floor(bandWidth / cellW),
			Math.ceil(Math.sqrt(isolated.length * 1.6))
		);
		const top = linked.length ? bandHeight + BAND_GAP : 0;
		isolated.forEach((node, i) => {
			positions.set(node.id, {
				x: (i % cols) * cellW,
				y: top + Math.floor(i / cols) * cellH
			});
		});
	}

	return positions;
}
