<script lang="ts">
	import { setContext, untrack } from 'svelte';
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
		type Connection
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import { SvelteSet } from 'svelte/reactivity';
	import DomainNodeComponent from './DomainNode.svelte';
	import {
		flattenTree,
		layoutTree,
		subtreeIds,
		visibleIds,
		NODE_WIDTH,
		NODE_HEIGHT,
		type FlatTree,
		type OrgTreeNode
	} from './tree';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
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

	const tree = $derived<FlatTree>(flattenTree(movableTree, receivingTree));
	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let instructionsOpen = $state(true);
	let busy = $state(false);

	// Highlight state lives outside `nodes` on purpose: rewriting the nodes array
	// mid-drag would swap the object xyflow is currently dragging.
	const drag = $state<{ draggingId: string | null; targetId: string | null; blocked: string[] }>({
		draggingId: null,
		targetId: null,
		blocked: []
	});

	// Real instances run to hundreds of domains, which no single canvas can show at a
	// readable zoom, so everything below the top level starts folded.
	const collapsed = new SvelteSet<string>();
	let collapseInitialised = false;
	// Bumped by every fold/unfold. Watching `collapsed.size` instead would miss a
	// change that adds and removes in the same tick.
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

	function expandAll() {
		collapsed.clear();
		collapseVersion += 1;
	}

	function collapseAll() {
		collapseBelowTopLevel();
		collapseVersion += 1;
	}

	function buildGraph() {
		const positions = layoutTree(tree, collapsed);
		const visible = visibleIds(tree, collapsed);

		nodes = [...tree.byId.values()]
			.filter((node) => visible.has(node.id))
			.map((node) => ({
				id: node.id,
				type: 'domain',
				position: positions[node.id] ?? { x: 0, y: 0 },
				data: {
					label: node.name,
					contentType: node.contentType,
					childCount: node.childCount,
					descendantCount: node.descendantCount,
					collapsed: collapsed.has(node.id),
					movable: node.movable,
					isRoot: node.parentId === null
				},
				draggable: node.parentId !== null && node.movable && node.contentType === 'DO',
				deletable: false,
				connectable: true
			}));

		edges = [...tree.byId.values()]
			.filter((node) => node.parentId !== null && visible.has(node.id))
			.map((node) => ({
				id: `e-${node.parentId}-${node.id}`,
				source: node.parentId!,
				target: node.id,
				type: 'smoothstep',
				deletable: false,
				selectable: false,
				markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' }
			}));
	}

	// Build synchronously, before mount: the `fitView` prop frames the graph as xyflow
	// initialises, so populating `nodes` from an effect instead would hand it an empty
	// canvas to fit and leave the tree parked off-screen.
	collapseBelowTopLevel();
	collapseInitialised = true;
	buildGraph();

	// Rebuild whenever the server data changes (after invalidateAll following a move,
	// a rename or a sub-domain creation) or whenever a branch is folded.
	$effect(() => {
		void tree;
		void collapseVersion;
		untrack(() => {
			if (!collapseInitialised) {
				collapseBelowTopLevel();
				collapseInitialised = true;
			}
			for (const id of [...collapsed]) {
				if (!tree.byId.has(id)) collapsed.delete(id);
			}
			buildGraph();
		});
	});

	let flowInstance: ReturnType<typeof useSvelteFlow> | null = null;

	function handleFlowInit() {
		// `useSvelteFlow()` has to run inside `oninit`: this component is the parent
		// of <SvelteFlow>, so the xyflow context only exists once the flow mounts.
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
	function requestReparent(childId: string, newParentId: string) {
		const reason = rejectionReason(childId, newParentId);
		if (reason) {
			toastStore.trigger({ message: reason, background: 'preset-tonal-warning' });
			buildGraph();
			return;
		}

		const child = tree.byId.get(childId)!;
		const newParent = tree.byId.get(newParentId)!;
		const oldParent = child.parentId ? tree.byId.get(child.parentId) : null;
		const carried =
			child.descendantCount > 0
				? ` and its ${child.descendantCount} nested domain${child.descendantCount > 1 ? 's' : ''}`
				: '';

		// Plain text only: ModalSettings.body is documented as accepting HTML, but
		// Modal.svelte interpolates it as text, so any markup would show as tags.
		const oldParentName = oldParent?.name ?? 'Global';
		const modal: ModalSettings = {
			type: 'confirm',
			title: 'Move domain',
			body:
				`Move "${child.name}"${carried} from "${oldParentName}" to "${newParent.name}". ` +
				`This changes access, not just the drawing: anyone holding a role on "${newParent.name}" ` +
				`will gain that access over "${child.name}" and everything inside it, and access ` +
				`inherited from "${oldParentName}" will be lost.`,
			buttonTextConfirm: 'Move domain',
			response: async (confirmed: boolean) => {
				if (!confirmed) {
					buildGraph();
					return;
				}
				busy = true;
				const ok = await patchParentFolder(childId, newParentId);
				busy = false;
				if (ok) {
					// Unfold the destination, or the domain would appear to vanish into a
					// collapsed branch.
					collapsed.delete(newParentId);
					collapseVersion += 1;
					toastStore.trigger({
						message: `"${child.name}" moved under "${newParent.name}"`,
						background: 'preset-tonal-success'
					});
					await invalidateAll();
				} else {
					buildGraph();
				}
			}
		};
		modalStore.trigger(modal);
	}

	function nodeCentre(node: Node) {
		return {
			x: node.position.x + NODE_WIDTH / 2,
			y: node.position.y + NODE_HEIGHT / 2
		};
	}

	// xyflow hands node-drag handlers ONE object — `{ targetNode, nodes, event }` — not
	// the (event, node) pair the React API uses. `nodes` holds the dragged selection.
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
		// A 1x1 probe at the dragged node's centre, so a domain only counts as a drop
		// target when it is actually being pointed at — plain overlap would fire on
		// any brush past a neighbour.
		const centre = nodeCentre(node);
		const hits =
			flowInstance?.getIntersectingNodes({ x: centre.x, y: centre.y, width: 1, height: 1 }) ?? [];
		const hit = hits.find((n) => n.id !== node.id);
		if (!hit) return null;
		return rejectionReason(node.id, hit.id) === null ? hit.id : null;
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
		// The community FolderForm doesn't render a parent_folder picker, but the form
		// posts with dataType 'json' — the whole `form.data` object goes over the wire,
		// rendered or not — so seeding it here is enough to nest the new domain.
		folderModel.createForm.data.parent_folder = parentId;
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
		if (!tree.rootId) return;
		requestReparent(folderId, tree.rootId);
	}

	setContext('domainBoard', {
		drag,
		renameDomain,
		createSubDomain,
		detachToRoot,
		toggleCollapse
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
		<Panel position="top-right">
			<div class="flex gap-1">
				<button
					type="button"
					class="btn preset-filled-surface-500 text-sm shadow"
					onclick={expandAll}
				>
					<i class="fa-solid fa-angles-down mr-1"></i>Expand all
				</button>
				<button
					type="button"
					class="btn preset-filled-surface-500 text-sm shadow"
					onclick={collapseAll}
				>
					<i class="fa-solid fa-angles-up mr-1"></i>Collapse
				</button>
				<button
					type="button"
					class="btn preset-filled-surface-500 text-sm shadow"
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
					onclick={() => (instructionsOpen = !instructionsOpen)}
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
						<ul class="list-inside list-disc space-y-0.5">
							<li>
								Click the <span class="font-mono">−</span>/<span class="font-mono">+</span> count on a
								domain to fold or unfold its branch
							</li>
							<li>Drag a domain onto another to make it a sub-domain</li>
							<li>Or drag the right handle of the new parent onto the domain to move</li>
							<li>
								Hover a domain and click the <span class="font-semibold">＋</span> badge to nest a new
								one
							</li>
							<li>Click the ↰ icon to move a domain back up to the top level</li>
							<li>Double-click a name to rename it</li>
							<li>Layout is computed from the hierarchy — a drag that isn't a move snaps back</li>
						</ul>
						<div class="mt-1.5 rounded bg-warning-100 px-2 py-1 text-warning-800">
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
	/* `colorMode` adds `.dark` to `.svelte-flow`, but the explicit background-color
	   above would otherwise win, so flip it back here. */
	:global(.dark .svelte-flow) {
		background-color: var(--color-surface-950);
	}
	:global(.svelte-flow .svelte-flow__edge-path) {
		stroke-width: 2;
	}
</style>
