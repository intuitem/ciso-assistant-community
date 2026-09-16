<script lang="ts">
	import { setContext, tick, untrack } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import {
		SvelteFlow,
		useSvelteFlow,
		Controls,
		Background,
		BackgroundVariant,
		MiniMap,
		Panel,
		MarkerType,
		type Node,
		type Edge,
		type Connection,
		type OnConnectEnd
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import { SvelteSet } from 'svelte/reactivity';
	import DomainNodeComponent from './DomainNode.svelte';
	import {
		flattenTree,
		layoutTree,
		subtreeIds,
		visibleIds,
		dropZone,
		contains,
		loadOrientation,
		saveOrientation,
		loadInstructionsOpen,
		saveInstructionsOpen,
		loadDraft,
		saveDraft,
		clearDraft,
		applyDraftToTree,
		isDeletableLeaf,
		NODE_WIDTH,
		NODE_HEIGHT,
		type FlatTree,
		type OrgTreeNode,
		type Orientation,
		type Draft,
		type DraftBaseline,
		type DeleteDraft
	} from './tree';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ApplyConfirmModal from './ApplyConfirmModal.svelte';
	import { resolvedTheme } from '$lib/utils/theme';

	interface Props {
		movableTree: OrgTreeNode | null;
		receivingTree: OrgTreeNode | null;
		folderModel: any;
	}

	let { movableTree, receivingTree, folderModel }: Props = $props();

	const toastStore = getToastStore();
	const modalStore = getModalStore();

	const nodeTypes = { domain: DomainNodeComponent };

	const liveTree = $derived<FlatTree>(flattenTree(movableTree, receivingTree));

	// Everything downstream reads `tree`, so the overlay gives proposals the same
	// layout, drop zones and cycle checks as reality — no second code path.
	const stored = loadDraft();
	let draft = $state<Draft>(stored.moves);
	let draftBaseline = $state<DraftBaseline>(stored.baseline);
	let deleteDraft = $state<DeleteDraft>(stored.deletes ?? []);
	const tree = $derived<FlatTree>(applyDraftToTree(liveTree, draft));
	const pendingCount = $derived(Object.keys(draft).length + deleteDraft.length);
	let applying = $state(false);
	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let instructionsOpen = $state(loadInstructionsOpen());
	let busy = $state(false);
	let orientation = $state<Orientation>(loadOrientation());
	// Which way a domain's children lie, for prose that has to point somewhere.
	const childrenLie = $derived(orientation === 'horizontal' ? 'to its right' : 'below it');
	const sourceEdge = $derived(orientation === 'horizontal' ? 'right' : 'bottom');

	// Outside `nodes`: rewriting that array mid-drag swaps the object xyflow is dragging.
	const drag = $state<{ draggingId: string | null; targetId: string | null; blocked: string[] }>({
		draggingId: null,
		targetId: null,
		blocked: []
	});

	// Hundreds of domains don't fit at a readable zoom, so below top level starts folded.
	const collapsed = new SvelteSet<string>();
	let collapseInitialised = false;
	// Watching `collapsed.size` would miss an add and remove in the same tick.
	let collapseVersion = $state(0);

	function collapseBelowTopLevel() {
		collapsed.clear();
		for (const node of tree.byId.values()) {
			if (node.depth >= 1 && node.childCount > 0) collapsed.add(node.id);
		}
	}

	function toggleCollapse(folderId: string) {
		if (collapsed.has(folderId)) collapsed.delete(folderId);
		else collapsed.add(folderId);
		collapseVersion += 1;
	}

	async function toggleOrientation() {
		orientation = orientation === 'horizontal' ? 'vertical' : 'horizontal';
		saveOrientation(orientation);
		// `tick()` only flushes Svelte; xyflow copies positions in an effect of its
		// own, so fitting before that lands measures the old bounds.
		await tick();
		requestAnimationFrame(() =>
			requestAnimationFrame(() => flowInstance?.fitView({ duration: 300, padding: 0.1 }))
		);
	}

	function expandAll() {
		collapsed.clear();
		collapseVersion += 1;
	}

	function collapseAll() {
		collapseBelowTopLevel();
		collapseVersion += 1;
	}

	function buildGraph() {
		const positions = layoutTree(tree, collapsed, orientation);
		const visible = visibleIds(tree, collapsed);

		nodes = [...tree.byId.values()]
			.filter((node) => visible.has(node.id))
			.map((node) => ({
				id: node.id,
				type: 'domain',
				position: positions[node.id] ?? { x: 0, y: 0 },
				data: {
					label: node.name,
					childCount: node.childCount,
					descendantCount: node.descendantCount,
					collapsed: collapsed.has(node.id),
					contentCount: node.contentCount,
					subtreeContentCount: node.subtreeContentCount,
					deletable: isDeletableLeaf(tree, node.id),
					stagedForDelete: deleteDraft.includes(node.id),
					movable: node.movable,
					canReceive: node.canReceive,
					isRoot: node.parentId === null,
					staged: draft[node.id] !== undefined,
					orientation
				},
				draggable: node.parentId !== null && node.movable && node.contentType === 'DO',
				deletable: false,
				connectable: true
			}));

		edges = [...tree.byId.values()]
			.filter((node) => node.parentId !== null && visible.has(node.id))
			.map((node) => {
				const staged = draft[node.id] !== undefined;
				return {
					id: `e-${node.parentId}-${node.id}`,
					source: node.parentId!,
					target: node.id,
					type: 'smoothstep',
					deletable: false,
					selectable: false,
					animated: staged,
					style: staged ? 'stroke: var(--color-warning-500); stroke-width: 2.5;' : undefined,
					markerEnd: {
						type: MarkerType.ArrowClosed,
						color: staged ? 'var(--color-warning-500)' : 'var(--color-surface-600)'
					}
				};
			});
	}

	// Before mount: `fitView` frames the graph at init, so filling `nodes` from an
	// effect would hand it an empty canvas and park the tree off-screen.
	collapseBelowTopLevel();
	collapseInitialised = true;
	buildGraph();

	$effect(() => {
		void tree;
		void collapseVersion;
		void orientation;
		void pendingCount;
		void deleteDraft;
		untrack(() => {
			if (!collapseInitialised) {
				collapseBelowTopLevel();
				collapseInitialised = true;
			}
			// Dropping the current key mid-iteration is well-defined for a Set.
			for (const id of collapsed) {
				if (!tree.byId.has(id)) collapsed.delete(id);
			}
			buildGraph();
		});
	});

	let flowInstance: ReturnType<typeof useSvelteFlow> | null = null;

	function handleFlowInit() {
		// Must run in `oninit`: this component is the parent of <SvelteFlow>, so the
		// xyflow context only exists once the flow mounts.
		flowInstance = useSvelteFlow();
	}

	/** Why a given move is refused, or null when it is allowed. */
	function rejectionReason(childId: string, newParentId: string): string | null {
		const child = tree.byId.get(childId);
		const parent = tree.byId.get(newParentId);
		if (!child || !parent) return 'Unknown domain';
		if (child.parentId === null) return 'The Global root has no parent and cannot be moved';
		if (child.contentType !== 'DO') return 'Only domains can be re-parented here';
		if (!child.movable) return `You don't have permission to modify "${child.name}"`;
		// The server refuses the whole batch if a move touches a staged delete.
		if (deleteDraft.includes(childId)) return `"${child.name}" is staged for deletion`;
		if (deleteDraft.includes(newParentId)) return `"${parent.name}" is staged for deletion`;
		if (!parent.canReceive)
			return `You don't have permission to add domains under "${parent.name}"`;
		if (childId === newParentId) return 'A domain cannot be its own parent';
		if (child.parentId === newParentId) return `"${child.name}" is already under "${parent.name}"`;
		if (subtreeIds(tree, childId).has(newParentId)) {
			return `"${parent.name}" sits below "${child.name}" — that would make a cycle`;
		}
		return null;
	}

	async function patchParentFolder(childId: string, newParentId: string): Promise<boolean> {
		try {
			const res = await fetch(`/folders/${childId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ parent_folder: newParentId })
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				const detail = err?.parent_folder ?? err?.detail ?? err?.non_field_errors ?? 'Move failed';
				toastStore.trigger({
					message: typeof detail === 'string' ? detail : JSON.stringify(detail),
					background: 'preset-tonal-error'
				});
				return false;
			}
			return true;
		} catch {
			toastStore.trigger({
				message: 'Network error moving the domain',
				background: 'preset-tonal-error'
			});
			return false;
		}
	}

	/**
	 * Re-parenting is not a cosmetic rearrangement: the folder tree is what the IAM
	 * resolves role assignments against, so a move silently changes who can reach the
	 * domain's contents. Always spell that out before committing.
	 */
	/** Stage a move instead of writing it; the access impact is reviewed once, for the
	 * whole shape, in `applyDraft`. */
	function requestReparent(childId: string, newParentId: string) {
		// applyDraft captured the draft already; anything staged now would be cleared.
		if (busy) return;
		const reason = rejectionReason(childId, newParentId);
		if (reason) {
			toastStore.trigger({ message: reason, background: 'preset-tonal-warning' });
			buildGraph();
			return;
		}

		// The LIVE parent, captured once: re-staging must not overwrite it with a
		// position that only existed in the draft.
		if (draftBaseline[childId] === undefined) {
			draftBaseline = {
				...draftBaseline,
				[childId]: liveTree.byId.get(childId)?.parentId ?? null
			};
		}

		const next = { ...draft, [childId]: newParentId };
		// Moving back to the start is not a change.
		if (draftBaseline[childId] === newParentId) {
			delete next[childId];
			const baseline = { ...draftBaseline };
			delete baseline[childId];
			draftBaseline = baseline;
		}
		draft = next;
		persistDraft();

		// Or the domain appears to vanish into a folded branch.
		collapsed.delete(newParentId);
		collapseVersion += 1;
	}

	function persistDraft() {
		saveDraft({ moves: draft, baseline: draftBaseline, deletes: deleteDraft });
	}

	/** Only offered for an empty leaf of the DRAFTED tree, so emptying a domain by
	 * dragging its children out unlocks removing it in the same apply. */
	function stageDelete(folderId: string) {
		if (busy) return;
		const node = tree.byId.get(folderId);
		if (!node) return;
		if (!isDeletableLeaf(tree, folderId)) {
			toastStore.trigger({
				message: `"${node.name}" still holds something. Only an empty domain with no sub-domains can be deleted here.`,
				background: 'preset-tonal-warning'
			});
			return;
		}
		// The server refuses move-and-delete of the same folder; don't stage it.
		if (draft[folderId] !== undefined) {
			const next = { ...draft };
			delete next[folderId];
			draft = next;
			const baseline = { ...draftBaseline };
			delete baseline[folderId];
			draftBaseline = baseline;
		}
		deleteDraft = [...deleteDraft, folderId];
		persistDraft();
	}

	function unstageDelete(folderId: string) {
		if (busy) return;
		deleteDraft = deleteDraft.filter((id) => id !== folderId);
		persistDraft();
	}

	function discardDraft() {
		modalStore.trigger({
			type: 'confirm',
			title: 'Discard proposal',
			body: `Discard all ${pendingCount} staged move${pendingCount > 1 ? 's' : ''}? The domains go back to where they actually are.`,
			buttonTextConfirm: 'Discard',
			response: (confirmed: boolean) => {
				if (!confirmed) return;
				draft = {};
				draftBaseline = {};
				deleteDraft = [];
				clearDraft();
			}
		});
	}

	function draftSummary(): string[] {
		const deletions = deleteDraft.map((id) => `delete  ${liveTree.byId.get(id)?.name ?? id}`);
		return [...moveSummary(), ...deletions];
	}

	function moveSummary(): string[] {
		return Object.entries(draft).map(([childId, parentId]) => {
			const child = liveTree.byId.get(childId);
			const target = liveTree.byId.get(parentId);
			const from = child?.parentId ? liveTree.byId.get(child.parentId)?.name : 'Global';
			const carried = child?.descendantCount ? ` (+${child.descendantCount} nested)` : '';
			return `${child?.name ?? childId}${carried}:  ${from} → ${target?.name ?? parentId}`;
		});
	}

	async function postReorganize(moves: unknown[], deletes: string[]) {
		const res = await fetch('/experimental/domain-board/reorganize', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ moves, deletes: deletes.map((folder) => ({ folder })) })
		});
		return { status: res.status, body: await res.json().catch(() => ({})) };
	}

	async function runApply(moves: unknown[], deletes: string[]) {
		applying = true;
		busy = true;
		let status: number;
		let body: any;
		try {
			({ status, body } = await postReorganize(moves, deletes));
		} catch {
			toastStore.trigger({
				message: 'Could not reach the server — nothing was applied.',
				background: 'preset-tonal-error'
			});
			return;
		} finally {
			applying = false;
			busy = false;
		}

		if (status === 409) {
			// Staleness, or a staged delete no longer targeting an empty leaf. Nothing
			// was applied either way, so the draft is still good.
			const detail = (body.conflicts ?? [])
				.map((c: any) => `${c.name ?? c.folder} (${c.reason})`)
				.join(', ');
			toastStore.trigger({
				message: `Nothing applied — the tree changed since you drafted: ${detail}. Reload to see it as it stands.`,
				background: 'preset-tonal-warning',
				timeout: 14000
			});
			return;
		}

		if (status !== 200) {
			const detail = body?.parent_folder ?? body?.moves ?? body?.detail ?? 'Apply failed';
			toastStore.trigger({
				message: typeof detail === 'string' ? detail : JSON.stringify(detail),
				background: 'preset-tonal-error'
			});
			return;
		}

		draft = {};
		draftBaseline = {};
		deleteDraft = [];
		clearDraft();
		const parts = [];
		if (body.applied) parts.push(`${body.applied} move${body.applied === 1 ? '' : 's'}`);
		if (body.deleted) parts.push(`${body.deleted} deletion${body.deleted === 1 ? '' : 's'}`);
		toastStore.trigger({
			message: `Applied ${parts.join(' and ') || 'nothing'}.`,
			background: 'preset-tonal-success'
		});
		await invalidateAll();
	}

	/** The one irreversible step, so it asks for a typed confirmation. No undo: an
	 * inverse goes stale as soon as anyone else touches the tree. */
	function applyDraft() {
		const moves = Object.entries(draft).map(([folder, parent_folder]) => ({
			folder,
			parent_folder,
			from_parent: draftBaseline[folder] ?? null
		}));

		const deletes = [...deleteDraft];
		modalStore.trigger({
			type: 'component',
			component: {
				ref: ApplyConfirmModal,
				props: {
					moves: draftSummary(),
					destructive: deletes.length > 0,
					onConfirm: () => void runApply(moves, deletes)
				}
			}
		});
	}

	function nodeCentre(node: Node) {
		return {
			x: node.position.x + NODE_WIDTH / 2,
			y: node.position.y + NODE_HEIGHT / 2
		};
	}

	// xyflow passes ONE object here, not the (event, node) pair the React API uses.
	type NodeDragArgs = { targetNode: Node | null; nodes: Node[]; event: MouseEvent | TouchEvent };

	function draggedNode({ targetNode, nodes: dragged }: NodeDragArgs): Node | null {
		return targetNode ?? dragged[0] ?? null;
	}

	function handleNodeDragStart(args: NodeDragArgs) {
		const node = draggedNode(args);
		if (!node) return;
		drag.draggingId = node.id;
		drag.targetId = null;
		drag.blocked = [...tree.byId.keys()].filter(
			(id) => id !== node.id && rejectionReason(node.id, id) !== null
		);
	}

	function candidateUnderCursor(node: Node): string | null {
		// Centre against each drop zone rather than requiring overlap; zones tile, so
		// at most one claims the point.
		const centre = nodeCentre(node);
		for (const other of nodes) {
			if (other.id === node.id) continue;
			if (!contains(dropZone(other.position, orientation), centre)) continue;
			return rejectionReason(node.id, other.id) === null ? other.id : null;
		}
		return null;
	}

	function handleNodeDrag(args: NodeDragArgs) {
		const node = draggedNode(args);
		if (!node) return;
		drag.targetId = candidateUnderCursor(node);
	}

	function handleNodeDragStop(args: NodeDragArgs) {
		const node = draggedNode(args);
		const target = node ? candidateUnderCursor(node) : null;
		drag.draggingId = null;
		drag.targetId = null;
		drag.blocked = [];
		if (node && target) {
			requestReparent(node.id, target);
		} else {
			// Positions are derived from the hierarchy, so anything that isn't a move
			// snaps back. That snap is the "nothing happened" signal.
			buildGraph();
		}
	}

	function isValidConnection(connection: Edge | Connection): boolean {
		if (!connection.source || !connection.target) return false;
		return rejectionReason(connection.target, connection.source) === null;
	}

	function handleConnect(connection: Connection) {
		if (!connection.source || !connection.target) return;
		// source is the prospective parent, target the domain being moved.
		requestReparent(connection.target, connection.source);
	}

	// Unlike the node-drag handlers, this one really does take (event, state).
	const handleConnectEnd: OnConnectEnd = (_event, connectionState) => {
		// xyflow reports `isValid === null` for a release over empty canvas.
		if (!connectionState || connectionState.isValid !== null) return;
		const parentId = connectionState.fromNode?.id;
		const parent = parentId ? tree.byId.get(parentId) : null;
		if (!parent) return;
		if (!parent.canReceive) {
			toastStore.trigger({
				message: `You don't have permission to add domains under "${parent.name}"`,
				background: 'preset-tonal-warning'
			});
			return;
		}
		createSubDomain(parent.id, parent.name);
	};

	async function renameDomain(folderId: string, name: string): Promise<boolean> {
		try {
			const res = await fetch(`/folders/${folderId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name })
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				const detail = err?.name ?? err?.detail ?? 'Rename failed';
				toastStore.trigger({
					message: typeof detail === 'string' ? detail : JSON.stringify(detail),
					background: 'preset-tonal-error'
				});
				return false;
			}
			nodes = nodes.map((n) =>
				n.id === folderId ? { ...n, data: { ...n.data, label: name } } : n
			);
			void invalidateAll();
			return true;
		} catch {
			toastStore.trigger({
				message: 'Network error renaming the domain',
				background: 'preset-tonal-error'
			});
			return false;
		}
	}

	function createSubDomain(parentId: string, parentName: string) {
		// The form posts with dataType 'json', so `form.data` goes over the wire whether
		// or not a parent_folder field is rendered.
		folderModel.createForm.data.parent_folder = parentId;
		collapsed.delete(parentId);
		collapseVersion += 1;
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: folderModel.createForm,
				model: folderModel,
				debug: false,
				invalidateAll: true
			}
		};
		modalStore.trigger({
			type: 'component',
			component: modalComponent,
			title: `New domain under "${parentName}"`
		});
	}

	function detachToRoot(folderId: string) {
		if (busy || !tree.rootId) return;
		requestReparent(folderId, tree.rootId);
	}

	setContext('domainBoard', {
		drag,
		renameDomain,
		createSubDomain,
		detachToRoot,
		toggleCollapse,
		stageDelete,
		unstageDelete
	});
</script>

<div
	class="relative h-full overflow-hidden rounded-base border border-surface-200-800 bg-surface-50-950"
>
	<SvelteFlow
		bind:nodes
		bind:edges
		colorMode={$resolvedTheme}
		{nodeTypes}
		{isValidConnection}
		onconnect={handleConnect}
		onconnectend={handleConnectEnd}
		onnodedragstart={handleNodeDragStart}
		onnodedrag={handleNodeDrag}
		onnodedragstop={handleNodeDragStop}
		oninit={handleFlowInit}
		zoomOnDoubleClick={false}
		nodesDraggable={!busy}
		fitView
		fitViewOptions={{ padding: 0.1 }}
		minZoom={0.05}
		proOptions={{ hideAttribution: true }}
	>
		<Background variant={BackgroundVariant.Dots} gap={20} />
		<Controls showLock={false} />
		<MiniMap />
		{#if drag.draggingId}
			{@const moving = tree.byId.get(drag.draggingId)}
			{@const landing = drag.targetId ? tree.byId.get(drag.targetId) : null}
			<Panel position="bottom-center">
				<div
					class="rounded-base border px-3 py-1.5 text-xs font-medium shadow-lg
					{landing
						? 'border-success-400 bg-success-50-950 text-success-700-300'
						: 'border-surface-300-700 bg-surface-100-900 text-surface-600-400'}"
				>
					{#if landing}
						<i class="fa-solid fa-arrow-turn-down mr-1"></i>
						Release to nest "{moving?.name}" under "{landing.name}"
					{:else}
						<i class="fa-solid fa-hand-pointer mr-1"></i>
						Drop on a domain — or just {childrenLie} — to nest "{moving?.name}" under it
					{/if}
				</div>
			</Panel>
		{/if}
		<Panel position="top-right">
			<div
				class="flex items-center gap-1 rounded-base border border-surface-300-700 bg-surface-100-900 p-1 shadow-sm"
			>
				{#if pendingCount > 0}
					<button
						type="button"
						class="btn btn-sm preset-filled-warning-500"
						disabled={applying}
						onclick={applyDraft}
					>
						<i class="fa-solid fa-check mr-1"></i>Apply {pendingCount} change{pendingCount > 1
							? 's'
							: ''}
					</button>
					<button
						type="button"
						class="btn btn-sm preset-tonal-surface"
						disabled={applying}
						onclick={discardDraft}
					>
						<i class="fa-solid fa-rotate-left mr-1"></i>Discard
					</button>
					<div class="mx-0.5 h-5 w-px bg-surface-300-700"></div>
				{/if}
				<button
					type="button"
					class="btn btn-sm preset-tonal-surface"
					title={orientation === 'horizontal'
						? 'Switch to a top-down layout'
						: 'Switch to a left-to-right layout'}
					onclick={toggleOrientation}
				>
					<i
						class="fa-solid {orientation === 'horizontal'
							? 'fa-arrows-up-down'
							: 'fa-arrows-left-right'} mr-1"
					></i>{orientation === 'horizontal' ? 'Vertical' : 'Horizontal'}
				</button>
				<button type="button" class="btn btn-sm preset-tonal-surface" onclick={expandAll}>
					<i class="fa-solid fa-angles-down mr-1"></i>Expand all
				</button>
				<button type="button" class="btn btn-sm preset-tonal-surface" onclick={collapseAll}>
					<i class="fa-solid fa-angles-up mr-1"></i>Collapse
				</button>
				<button
					type="button"
					class="btn btn-sm preset-tonal-surface"
					onclick={() => flowInstance?.fitView({ duration: 250, padding: 0.1 })}
				>
					<i class="fa-solid fa-compress mr-1"></i>Fit
				</button>
			</div>
		</Panel>
		<Panel position="top-left">
			<div
				class="max-w-md rounded-base border border-surface-300-700 bg-surface-100-900 text-xs leading-relaxed text-surface-700-300 shadow-sm"
			>
				<button
					type="button"
					class="flex w-full cursor-pointer items-center justify-between rounded-base px-3 py-2 font-semibold hover:bg-surface-200-800"
					aria-expanded={instructionsOpen}
					aria-controls="domain-board-instructions"
					onclick={() => {
						instructionsOpen = !instructionsOpen;
						saveInstructionsOpen(instructionsOpen);
					}}
				>
					<span><i class="fa-solid fa-info-circle mr-1"></i>Instructions</span>
					<i class="fa-solid {instructionsOpen ? 'fa-chevron-up' : 'fa-chevron-down'} text-[10px]"
					></i>
				</button>
				{#if instructionsOpen}
					<div id="domain-board-instructions" class="px-3 pb-2">
						<div class="mb-1 text-surface-600-400">
							Convention: arrow <span class="font-mono">A → B</span> means
							<em>B is a sub-domain of A</em>.
						</div>
						<div
							class="mb-1.5 rounded border border-warning-200-800 bg-warning-50-950 px-2 py-1 text-warning-700-300"
						>
							<i class="fa-solid fa-flask mr-1"></i>Moves are staged, not saved. Rearrange freely,
							then <span class="font-semibold">Apply</span> to write them in one go. The draft survives
							a reload.
						</div>
						<div class="mt-1 mb-0.5 font-semibold text-surface-700-300">Move a domain</div>
						<ul class="list-inside list-disc space-y-0.5">
							<li>
								Drag it onto another domain — or into the empty space just {childrenLie}, where its
								sub-domains sit
							</li>
							<li>Click the ↰ icon to send it back up to the top level</li>
						</ul>
						<div class="mt-1.5 mb-0.5 font-semibold text-surface-700-300">Add a domain</div>
						<ul class="list-inside list-disc space-y-0.5">
							<li>Drag the handle on a domain's {sourceEdge} edge onto empty canvas</li>
							<li>
								Or hover it and click the <span class="font-semibold">＋</span> badge
							</li>
						</ul>
						<div class="mt-1.5 mb-0.5 font-semibold text-surface-700-300">Get around</div>
						<ul class="list-inside list-disc space-y-0.5">
							<li>
								Click the <span class="font-mono">−</span>/<span class="font-mono">+</span> count to fold
								or unfold a branch
							</li>
							<li>Double-click a name to rename it (renames save immediately)</li>
							<li>Layout follows the hierarchy — a drag that isn't a move snaps back</li>
						</ul>
						<div
							class="mt-1.5 rounded border border-warning-200-800 bg-warning-50-950 px-2 py-1 text-warning-700-300"
						>
							<i class="fa-solid fa-triangle-exclamation mr-1"></i>Moving a domain changes who can
							see its contents — role assignments follow the tree.
						</div>
					</div>
				{/if}
			</div>
		</Panel>
	</SvelteFlow>
</div>

<style>
	:global(.svelte-flow) {
		--xy-node-border-radius: var(--radius-base);
		--xy-edge-stroke: var(--color-surface-500);
		background-color: var(--color-surface-50);
	}
	/* `colorMode` adds `.dark`, but the background-color above would win. */
	:global(.dark .svelte-flow) {
		background-color: var(--color-surface-950);
	}
	:global(.svelte-flow .svelte-flow__edge-path) {
		stroke-width: 2;
	}
</style>
