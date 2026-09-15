import { browser } from '$app/environment';

export interface OrgTreeNode {
	name: string;
	uuid: string;
	// org_tree emits the RAW content_type code ('GL' | 'DO' | 'EN' | 'PE'), unlike
	// FolderReadSerializer which runs it through get_content_type_display() and so
	// returns a translated label. Never swap this source for the list endpoint.
	content_type?: string;
	viewable?: boolean;
	writable?: boolean;
	children?: OrgTreeNode[];
}

export interface DomainNode {
	id: string;
	name: string;
	contentType: string;
	parentId: string | null;
	depth: number;
	childCount: number;
	descendantCount: number;
	/** user holds change_folder here, so this node may be moved */
	movable: boolean;
	/** user holds add_folder here, so this node may become someone's parent */
	canReceive: boolean;
}

export interface XY {
	x: number;
	y: number;
}

export interface FlatTree {
	byId: Map<string, DomainNode>;
	childrenOf: Map<string, string[]>;
	rootId: string | null;
}

function collectWritable(node: OrgTreeNode | null, into: Set<string>): Set<string> {
	if (!node) return into;
	if (node.writable !== false) into.add(node.uuid);
	for (const child of node.children ?? []) collectWritable(child, into);
	return into;
}

/**
 * Flatten an org_tree response into a lookup keyed by folder id.
 *
 * `movableTree` and `receivingTree` are the same tree fetched with
 * `write_perm=change_folder` and `write_perm=add_folder`; a move needs the first
 * on the moved folder and the second on its new parent.
 */
export function flattenTree(
	movableTree: OrgTreeNode | null,
	receivingTree: OrgTreeNode | null
): FlatTree {
	const byId = new Map<string, DomainNode>();
	const childrenOf = new Map<string, string[]>();
	const movableIds = collectWritable(movableTree, new Set());
	const receivingIds = collectWritable(receivingTree, new Set());

	const visit = (node: OrgTreeNode, parentId: string | null, depth: number) => {
		const children = node.children ?? [];
		byId.set(node.uuid, {
			id: node.uuid,
			name: node.name,
			contentType: node.content_type ?? 'DO',
			parentId,
			depth,
			childCount: children.length,
			descendantCount: 0,
			movable: movableIds.has(node.uuid),
			canReceive: receivingIds.has(node.uuid)
		});
		childrenOf.set(
			node.uuid,
			children.map((c) => c.uuid)
		);
		for (const child of children) visit(child, node.uuid, depth + 1);
	};

	if (movableTree) visit(movableTree, null, 0);

	// Second pass: subtree sizes, computed bottom-up from the deepest nodes.
	const sorted = [...byId.values()].sort((a, b) => b.depth - a.depth);
	for (const node of sorted) {
		let total = 0;
		for (const childId of childrenOf.get(node.id) ?? []) {
			total += 1 + (byId.get(childId)?.descendantCount ?? 0);
		}
		node.descendantCount = total;
	}

	return { byId, childrenOf, rootId: movableTree?.uuid ?? null };
}

export const NODE_WIDTH = 210;
export const NODE_HEIGHT = 58;

/** Horizontal: depth runs left-to-right. Vertical: depth runs top-down (org chart). */
export type Orientation = 'horizontal' | 'vertical';

// Gaps differ per orientation because the node box is wide and short: siblings need
// less room when stacked than when placed side by side, and levels need more.
const GAPS = {
	horizontal: { depth: 90, sibling: 24 },
	vertical: { depth: 70, sibling: 28 }
} as const;

/**
 * The two axes of a layout. `depth` grows with distance from the root, `sibling` with
 * position among peers; the orientation decides which maps to x and which to y, so the
 * traversal below is written once and the geometry that follows it derives from here.
 */
function axes(orientation: Orientation) {
	const gap = GAPS[orientation];
	const horizontal = orientation === 'horizontal';
	return {
		depthPitch: (horizontal ? NODE_WIDTH : NODE_HEIGHT) + gap.depth,
		siblingPitch: (horizontal ? NODE_HEIGHT : NODE_WIDTH) + gap.sibling,
		siblingGap: gap.sibling,
		toXY: (depth: number, sibling: number): XY =>
			horizontal ? { x: depth, y: sibling } : { x: sibling, y: depth }
	};
}

function sortedChildren(tree: FlatTree, id: string): string[] {
	return [...(tree.childrenOf.get(id) ?? [])].sort((a, b) =>
		(tree.byId.get(a)?.name ?? '').localeCompare(tree.byId.get(b)?.name ?? '')
	);
}

/**
 * Tidy tree layout: distance from the root drives one axis, an in-order walk of the
 * leaves drives the other, and every parent centres on the span of its children.
 * Subtrees under a collapsed id are left out entirely, so collapsing genuinely shrinks
 * the canvas rather than just hiding ink.
 *
 * Positions are derived, never stored. A domain has exactly one parent
 * (`parent_folder` is an FK, not an M2M), so the arrangement is fully determined
 * by the hierarchy — there is nothing for a user to arrange by hand, and a drag
 * is therefore free to mean "re-parent" rather than "reposition".
 */
export function layoutTree(
	tree: FlatTree,
	collapsed: ReadonlySet<string>,
	orientation: Orientation
): Record<string, XY> {
	const positions: Record<string, XY> = {};
	if (!tree.rootId) return positions;
	const { depthPitch, siblingPitch, toXY } = axes(orientation);
	const along: Record<string, number> = {};
	let cursor = 0;

	const visit = (id: string, depth: number) => {
		const node = tree.byId.get(id);
		if (!node) return;
		const children = collapsed.has(id) ? [] : sortedChildren(tree, id);

		if (children.length === 0) {
			along[id] = cursor;
			cursor += siblingPitch;
		} else {
			for (const child of children) visit(child, depth + 1);
			along[id] = (along[children[0]] + along[children[children.length - 1]]) / 2;
		}
		positions[id] = toXY(depth * depthPitch, along[id]);
	};

	visit(tree.rootId, 0);
	return positions;
}

export interface Rect {
	x: number;
	y: number;
	width: number;
	height: number;
}

/**
 * The region that reads as "nest under this domain": the node's own box plus the gap
 * towards its children — to the right when horizontal, below when vertical.
 *
 * Requiring an exact overlap with the node made re-parenting fiddly to discover and
 * fiddly to hit. Because the layout is a strict grid, these bands tile the canvas —
 * one axis is exactly the sibling pitch, the other stops where the next level begins —
 * so widening the target costs no ambiguity: every point still has at most one owner,
 * and the band is where a child of that domain actually lands.
 */
export function dropZone(position: XY, orientation: Orientation): Rect {
	const { depthPitch, siblingGap } = axes(orientation);
	if (orientation === 'horizontal') {
		return {
			x: position.x,
			y: position.y - siblingGap / 2,
			width: depthPitch,
			height: NODE_HEIGHT + siblingGap
		};
	}
	return {
		x: position.x - siblingGap / 2,
		y: position.y,
		width: NODE_WIDTH + siblingGap,
		height: depthPitch
	};
}

export function contains(rect: Rect, point: XY): boolean {
	return (
		point.x >= rect.x &&
		point.x <= rect.x + rect.width &&
		point.y >= rect.y &&
		point.y <= rect.y + rect.height
	);
}

/** Ids reachable from the root without crossing a collapsed node. */
export function visibleIds(tree: FlatTree, collapsed: ReadonlySet<string>): Set<string> {
	const out = new Set<string>();
	if (!tree.rootId) return out;
	const stack = [tree.rootId];
	while (stack.length) {
		const current = stack.pop()!;
		if (out.has(current)) continue;
		out.add(current);
		if (!collapsed.has(current)) stack.push(...(tree.childrenOf.get(current) ?? []));
	}
	return out;
}

/** Ids of `id` and everything below it. */
export function subtreeIds(tree: FlatTree, id: string): Set<string> {
	const out = new Set<string>();
	const stack = [id];
	while (stack.length) {
		const current = stack.pop()!;
		if (out.has(current)) continue;
		out.add(current);
		stack.push(...(tree.childrenOf.get(current) ?? []));
	}
	return out;
}

const ORIENTATION_KEY = 'domainBoard:orientation';

/**
 * Orientation is the one thing worth remembering between visits. Unlike a saved
 * viewport — which strands the user the moment the hierarchy or fold state changes —
 * this is a pure preference, and the board always re-fits after applying it.
 */
export function loadOrientation(): Orientation {
	if (!browser) return 'horizontal';
	try {
		return localStorage.getItem(ORIENTATION_KEY) === 'vertical' ? 'vertical' : 'horizontal';
	} catch {
		return 'horizontal';
	}
}

export function saveOrientation(orientation: Orientation): void {
	if (!browser) return;
	try {
		localStorage.setItem(ORIENTATION_KEY, orientation);
	} catch {
		// ignore quota errors
	}
}
