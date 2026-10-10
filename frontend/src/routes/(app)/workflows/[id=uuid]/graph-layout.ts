import dagre from '@dagrejs/dagre';
import type { Edge, Node } from '@xyflow/svelte';

// Fallbacks for nodes not yet measured by Svelte Flow (first paint, or the
// load-time auto-layout racing the measurer). Rough per-type footprints.
const DEFAULT_SIZE: Record<string, { width: number; height: number }> = {
	terminal: { width: 60, height: 60 },
	trigger: { width: 220, height: 70 },
	condition: { width: 200, height: 110 },
	step: { width: 200, height: 70 }
};

/**
 * Layered left-to-right layout (dagre / Sugiyama): what the "Tidy up" button
 * runs, and what lays out graphs that arrive without positions (imported or
 * hand-written YAML). Returns top-left positions keyed by node id — dagre
 * yields centers, Svelte Flow anchors top-left.
 *
 * Dagre is port-blind, so condition nodes get two branch-order assists: their
 * outgoing edges are fed in branch display order (seeding dagre's crossing
 * minimization), and a post-pass permutes same-rank sibling targets so their
 * vertical order matches the branch rows on the node — wires leave the node
 * top-to-bottom without crossing.
 */
export function computeLayout(nodes: Node[], edges: Edge[]): Map<string, { x: number; y: number }> {
	const graph = new dagre.graphlib.Graph();
	graph.setGraph({
		rankdir: 'LR',
		ranksep: 90,
		nodesep: 45,
		edgesep: 25,
		marginx: 40,
		marginy: 40
	});
	graph.setDefaultEdgeLabel(() => ({}));

	const sizeOf = (node: Node) => ({
		width: node.measured?.width ?? DEFAULT_SIZE[node.type ?? 'step']?.width ?? 200,
		height: node.measured?.height ?? DEFAULT_SIZE[node.type ?? 'step']?.height ?? 70
	});

	for (const node of nodes) graph.setNode(node.id, sizeOf(node));
	for (const edge of sortEdgesByBranchOrder(nodes, edges)) {
		graph.setEdge(edge.source, edge.target);
	}

	dagre.layout(graph);

	const positions = new Map(
		nodes.map((node) => {
			const placed = graph.node(node.id);
			const { width, height } = sizeOf(node);
			return [
				node.id,
				{ x: Math.round(placed.x - width / 2), y: Math.round(placed.y - height / 2) }
			] as const;
		})
	);
	// Rank membership must be judged on dagre's CENTERS: top-left x differs
	// between same-rank nodes of different widths.
	const centers = new Map(nodes.map((node) => [node.id, graph.node(node.id).x]));

	alignBranchTargets(nodes, edges, positions, centers);
	return positions;
}

/** Branch ids of a condition node in display order (default pinned last). */
function branchOrder(node: Node): string[] {
	const branches: any[] = (node.data?.domain as any)?.branches ?? [];
	return [...branches]
		.sort(
			(a, b) => Number(!!a.is_default) - Number(!!b.is_default) || (a.order ?? 0) - (b.order ?? 0)
		)
		.map((branch) => branch.id);
}

/** Feed dagre condition-node edges in branch display order — insertion order
 * seeds its initial rank ordering, which crossing minimization then respects
 * far more often than not. */
function sortEdgesByBranchOrder(nodes: Node[], edges: Edge[]): Edge[] {
	const rankByBranch = new Map<string, number>();
	for (const node of nodes) {
		if ((node.data?.domain as any)?.type !== 'condition') continue;
		branchOrder(node).forEach((branchId, index) => rankByBranch.set(branchId, index));
	}
	const rankOf = (edge: Edge) => {
		const branchId = (edge.data?.domain as any)?.source_branch;
		return branchId ? (rankByBranch.get(branchId) ?? 0) : 0;
	};
	return [...edges].sort((a, b) => a.source.localeCompare(b.source) || rankOf(a) - rankOf(b));
}

/** For each condition node: if its branch targets are exclusive to it (their
 * only incoming wire is this node's) and sit in the same rank, permute their
 * y positions so the top-to-bottom order matches the branch order. */
function alignBranchTargets(
	nodes: Node[],
	edges: Edge[],
	positions: Map<string, { x: number; y: number }>,
	centers: Map<string, number>
) {
	const incomingCount = new Map<string, number>();
	for (const edge of edges) {
		incomingCount.set(edge.target, (incomingCount.get(edge.target) ?? 0) + 1);
	}
	const targetByBranch = new Map<string, string>();
	for (const edge of edges) {
		const branchId = (edge.data?.domain as any)?.source_branch;
		if (branchId) targetByBranch.set(branchId, edge.target);
	}

	for (const node of nodes) {
		if ((node.data?.domain as any)?.type !== 'condition') continue;
		const targets = branchOrder(node)
			.map((branchId) => targetByBranch.get(branchId))
			.filter((t): t is string => !!t);
		// Eligible only when targets are distinct, single-parent, placed, and
		// share a rank (judged on centers) — permuting anything else could
		// collide with unrelated nodes.
		if (new Set(targets).size !== targets.length) continue;
		if (targets.some((t) => (incomingCount.get(t) ?? 0) !== 1 || !positions.get(t))) continue;
		const rankXs = targets.map((t) => centers.get(t) ?? 0);
		if (Math.max(...rankXs) - Math.min(...rankXs) > 1) continue;

		const ys = targets.map((t) => positions.get(t)!.y).sort((a, b) => a - b);
		targets.forEach((target, index) => {
			positions.set(target, { x: positions.get(target)!.x, y: ys[index] });
		});
	}
}
