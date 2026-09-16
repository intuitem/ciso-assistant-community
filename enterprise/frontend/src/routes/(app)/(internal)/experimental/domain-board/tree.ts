import { browser } from '$app/environment';

export interface OrgTreeNode {
	name: string;
	uuid: string;
	// RAW code ('GL'|'DO'|'EN'|'PE'). FolderReadSerializer returns a TRANSLATED label
	// instead, so never source this from the list endpoint.
	content_type?: string;
	viewable?: boolean;
	writable?: boolean;
	/** curated count of objects held directly by this folder (with_counts=true) */
	content_count?: number;
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
	/** objects held directly by this domain */
	contentCount: number;
	/** objects held by this domain and everything under it */
	subtreeContentCount: number;
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

/** Flatten org_tree into a lookup by id. The two trees are the same fetch with
 * `write_perm=change_folder` and `add_folder`: a move needs both. */
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
			contentCount: node.content_count ?? 0,
			subtreeContentCount: 0,
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

	// Bottom-up: subtree sizes and content totals. The server sends direct counts only.
	const sorted = [...byId.values()].sort((a, b) => b.depth - a.depth);
	for (const node of sorted) {
		let total = 0;
		let content = node.contentCount;
		for (const childId of childrenOf.get(node.id) ?? []) {
			const child = byId.get(childId);
			total += 1 + (child?.descendantCount ?? 0);
			content += child?.subtreeContentCount ?? 0;
		}
		node.descendantCount = total;
		node.subtreeContentCount = content;
	}

	return { byId, childrenOf, rootId: movableTree?.uuid ?? null };
}

export const NODE_WIDTH = 210;
export const NODE_HEIGHT = 58;

/** Horizontal: depth runs left-to-right. Vertical: depth runs top-down (org chart). */
export type Orientation = 'horizontal' | 'vertical';

// The node box is wide and short, so stacked siblings need less room than side-by-side.
const GAPS = {
	horizontal: { depth: 90, sibling: 24 },
	vertical: { depth: 70, sibling: 28 }
} as const;

/** Orientation decides which axis is x and which is y, so the traversal is written once. */
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
 * Tidy tree layout; collapsed subtrees are omitted, not hidden.
 *
 * Positions are derived, never stored — `parent_folder` is an FK, so the hierarchy
 * fully determines the arrangement, which frees a drag to mean "re-parent".
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
 * "Nest under this domain": the node plus the gap towards its children.
 *
 * Wider than the node on purpose. The bands tile exactly — one axis is the sibling
 * pitch, the other stops at the next level — so every point still has one owner.
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

/** Half-open: adjacent zones share an edge, and owning it twice would make the
 * winner depend on iteration order. */
export function contains(rect: Rect, point: XY): boolean {
	return (
		point.x >= rect.x &&
		point.x < rect.x + rect.width &&
		point.y >= rect.y &&
		point.y < rect.y + rect.height
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

const INSTRUCTIONS_KEY = 'domainBoard:instructionsOpen';

/** Starts closed; the choice is remembered so learners aren't re-collapsing it. */
export function loadInstructionsOpen(): boolean {
	if (!browser) return false;
	try {
		return localStorage.getItem(INSTRUCTIONS_KEY) === 'true';
	} catch {
		return false;
	}
}

export function saveInstructionsOpen(open: boolean): void {
	if (!browser) return;
	try {
		localStorage.setItem(INSTRUCTIONS_KEY, String(open));
	} catch {
		// ignore quota errors
	}
}

const ORIENTATION_KEY = 'domainBoard:orientation';

/** Safe to persist, unlike a viewport: the board always re-fits after applying it. */
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

/** folder id -> proposed parent id, for moves staged but not yet applied. */
export type Draft = Record<string, string>;
/** folder id -> the parent it had when the move was staged (optimistic concurrency). */
export type DraftBaseline = Record<string, string | null>;

export interface StoredDraft {
	moves: Draft;
	baseline: DraftBaseline;
	deletes: string[];
}

const DRAFT_KEY = 'domainBoard:draft';

/** A draft is a list of moves, never a tree snapshot: a snapshot would clobber or
 * conflict with concurrent changes to branches the draft never touched. */
export function loadDraft(): StoredDraft {
	if (!browser) return { moves: {}, baseline: {}, deletes: [] };
	try {
		const raw = localStorage.getItem(DRAFT_KEY);
		if (!raw) return { moves: {}, baseline: {}, deletes: [] };
		const parsed = JSON.parse(raw);
		return {
			moves: parsed?.moves && typeof parsed.moves === 'object' ? parsed.moves : {},
			baseline: parsed?.baseline && typeof parsed.baseline === 'object' ? parsed.baseline : {},
			deletes: Array.isArray(parsed?.deletes) ? parsed.deletes : []
		};
	} catch {
		return { moves: {}, baseline: {}, deletes: [] };
	}
}

export function saveDraft(draft: StoredDraft): void {
	if (!browser) return;
	try {
		localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
	} catch {
		// ignore quota errors
	}
}

export function clearDraft(): void {
	if (!browser) return;
	try {
		localStorage.removeItem(DRAFT_KEY);
	} catch {
		// ignore
	}
}

/** Overlay staged moves so a proposal renders through the same path as reality.
 * Moves whose folder or target has vanished are dropped; apply reports them. */
export function applyDraftToTree(tree: FlatTree, moves: Draft): FlatTree {
	if (Object.keys(moves).length === 0) return tree;

	const byId = new Map<string, DomainNode>();
	for (const [id, node] of tree.byId) byId.set(id, { ...node });

	// A stored draft is replayed against a tree that may have moved under it: the
	// live parent may since have become a descendant of the node being moved. The
	// resulting cycle is unreachable from the root, so both would silently vanish
	// from the canvas rather than loop. Skip the move; the server rejects it too.
	const wouldCycle = (id: string, parentId: string): boolean => {
		let cursor: string | null = parentId;
		for (let hops = 0; cursor !== null && hops <= byId.size; hops++) {
			if (cursor === id) return true;
			cursor = byId.get(cursor)?.parentId ?? null;
		}
		return cursor !== null; // never reached the root: already cyclic
	};

	for (const [id, parentId] of Object.entries(moves)) {
		const node = byId.get(id);
		if (!node || !byId.has(parentId) || node.parentId === null) continue;
		if (wouldCycle(id, parentId)) continue;
		node.parentId = parentId;
	}

	const childrenOf = new Map<string, string[]>();
	for (const id of byId.keys()) childrenOf.set(id, []);
	for (const node of byId.values()) {
		if (node.parentId !== null) childrenOf.get(node.parentId)?.push(node.id);
	}

	const drafted: FlatTree = { byId, childrenOf, rootId: tree.rootId };

	// The overlay invalidates depth and subtree sizes, and both are rendered.
	if (drafted.rootId) {
		const stack: Array<[string, number]> = [[drafted.rootId, 0]];
		while (stack.length) {
			const [id, depth] = stack.pop()!;
			const node = byId.get(id);
			if (!node) continue;
			node.depth = depth;
			node.childCount = childrenOf.get(id)?.length ?? 0;
			for (const child of childrenOf.get(id) ?? []) stack.push([child, depth + 1]);
		}
	}
	for (const node of [...byId.values()].sort((a, b) => b.depth - a.depth)) {
		let total = 0;
		let content = node.contentCount;
		for (const childId of childrenOf.get(node.id) ?? []) {
			const child = byId.get(childId);
			total += 1 + (child?.descendantCount ?? 0);
			content += child?.subtreeContentCount ?? 0;
		}
		node.descendantCount = total;
		node.subtreeContentCount = content;
	}

	return drafted;
}

/** folder ids staged for deletion. */
export type DeleteDraft = string[];

/** Read from the DRAFTED tree on purpose: staging children out makes a domain
 * deletable. Only decides the affordance; the server re-checks at apply time. */
export function isDeletableLeaf(tree: FlatTree, id: string): boolean {
	const node = tree.byId.get(id);
	if (!node || node.parentId === null) return false;
	if (node.contentType !== 'DO' || !node.movable) return false;
	if ((tree.childrenOf.get(id) ?? []).length > 0) return false;
	return node.contentCount === 0;
}
