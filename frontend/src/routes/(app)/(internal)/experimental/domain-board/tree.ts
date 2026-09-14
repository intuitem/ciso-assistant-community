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
const COLUMN_GAP = 90;
const ROW_GAP = 24;

function sortedChildren(tree: FlatTree, id: string): string[] {
	return [...(tree.childrenOf.get(id) ?? [])].sort((a, b) =>
		(tree.byId.get(a)?.name ?? '').localeCompare(tree.byId.get(b)?.name ?? '')
	);
}

/**
 * Tidy left-to-right tree layout: depth drives x, an in-order walk of the leaves
 * drives y, and every parent centres on the span of its children. Subtrees under a
 * collapsed id are left out entirely, so collapsing genuinely shrinks the canvas
 * rather than just hiding ink.
 *
 * Positions are derived, never stored. A domain has exactly one parent
 * (`parent_folder` is an FK, not an M2M), so the arrangement is fully determined
 * by the hierarchy — there is nothing for a user to arrange by hand, and a drag
 * is therefore free to mean "re-parent" rather than "reposition".
 */
export function layoutTree(tree: FlatTree, collapsed: ReadonlySet<string>): Record<string, XY> {
	const positions: Record<string, XY> = {};
	if (!tree.rootId) return positions;
	let cursorY = 0;

	const visit = (id: string, depth: number) => {
		const node = tree.byId.get(id);
		if (!node) return;
		const x = depth * (NODE_WIDTH + COLUMN_GAP);
		const children = collapsed.has(id) ? [] : sortedChildren(tree, id);

		if (children.length === 0) {
			positions[id] = { x, y: cursorY };
			cursorY += NODE_HEIGHT + ROW_GAP;
			return;
		}

		for (const child of children) visit(child, depth + 1);
		const first = positions[children[0]].y;
		const last = positions[children[children.length - 1]].y;
		positions[id] = { x, y: (first + last) / 2 };
	};

	visit(tree.rootId, 0);
	return positions;
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
