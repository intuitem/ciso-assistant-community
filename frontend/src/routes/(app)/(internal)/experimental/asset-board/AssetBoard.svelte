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

	import AssetNodeComponent from './AssetNode.svelte';
	import AssetEdgeComponent from './AssetEdge.svelte';
	import {
		loadPositions,
		savePositions,
		loadViewport,
		saveViewport as saveViewportLS,
		type XY
	} from './positions';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import { m } from '$paraglide/messages';

	interface AssetItem {
		id: string;
		name: string;
		ref_id?: string | null;
		// `type` from AssetListSerializer is `get_type_display()` — a TRANSLATED string
		// like "Primary"/"Primaire". Don't parse it; rely on `is_primary` instead.
		type: string;
		is_primary: boolean;
		folder?: { id: string; str?: string } | string | null;
		parent_assets?: Array<{ id: string; str?: string } | string>;
	}

	interface Props {
		assets: AssetItem[];
		folderId: string;
		assetModel: any;
		deleteForm: any;
	}

	let { assets, folderId, assetModel, deleteForm }: Props = $props();

	const toastStore = getToastStore();
	const modalStore = getModalStore();

	const nodeTypes = { asset: AssetNodeComponent };
	const edgeTypes = { asset: AssetEdgeComponent };

	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let positions = $state<Record<string, XY>>({});
	let instructionsOpen = $state(true);
	// drop coordinates + optional parent for the next asset created via the canvas
	let pendingPlacement = $state<XY | null>(null);
	let pendingParentId = $state<string | null>(null);
	let knownAssetIds = $state<Set<string>>(new Set());

	const GRID_COLS = 4;
	const GRID_X = 240;
	const GRID_Y = 140;

	function defaultPositionFor(index: number): XY {
		const col = index % GRID_COLS;
		const row = Math.floor(index / GRID_COLS);
		return { x: 60 + col * GRID_X, y: 60 + row * GRID_Y };
	}

	function buildGraph() {
		const inFolderIds = new Set(assets.map((a) => a.id));

		const externalParentCount: Record<string, number> = {};
		for (const a of assets) {
			let count = 0;
			for (const p of a.parent_assets ?? []) {
				const pid = typeof p === 'object' ? p.id : p;
				if (!inFolderIds.has(pid)) count += 1;
			}
			externalParentCount[a.id] = count;
		}

		const flowNodes: Node[] = assets.map((a, i) => {
			const saved = positions[a.id];
			return {
				id: a.id,
				type: 'asset',
				position: saved ?? defaultPositionFor(i),
				data: {
					label: a.name,
					refId: a.ref_id ?? '',
					// Always store the raw code on the node so locale never matters
					type: a.is_primary ? 'PR' : 'SP',
					externalLinkCount: externalParentCount[a.id] ?? 0
				},
				draggable: true,
				deletable: false,
				connectable: true
			};
		});

		const flowEdges: Edge[] = [];
		for (const a of assets) {
			for (const p of a.parent_assets ?? []) {
				const pid = typeof p === 'object' ? p.id : p;
				if (!inFolderIds.has(pid)) continue;
				flowEdges.push({
					id: `e-${pid}-${a.id}`,
					source: pid,
					target: a.id,
					type: 'asset',
					markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' }
				});
			}
		}

		nodes = flowNodes;
		edges = flowEdges;
		knownAssetIds = inFolderIds;
	}

	// Initial load from localStorage and graph build
	positions = loadPositions(folderId);
	buildGraph();

	// When the assets prop changes (after invalidateAll), rebuild
	$effect(() => {
		void assets;
		untrack(() => {
			const newIds = new Set(assets.map((a) => a.id));
			const added = [...newIds].filter((id) => !knownAssetIds.has(id));
			if (added.length > 0 && pendingPlacement) {
				// New asset(s) created via the canvas — place at pending drop coords
				const updated = { ...positions };
				for (const id of added) {
					updated[id] = pendingPlacement;
				}
				positions = updated;
				savePositions(folderId, updated);

				// If the create gesture started from a node handle, wire that parent now
				if (pendingParentId) {
					const parentToWire = pendingParentId;
					for (const newAssetId of added) {
						void patchParentAssets(newAssetId, [parentToWire]).then((ok) => {
							if (ok) invalidateAll();
						});
					}
				}
				pendingPlacement = null;
				pendingParentId = null;
			}
			buildGraph();
		});
	});

	let flowInstance: ReturnType<typeof useSvelteFlow> | null = null;

	function handleFlowInit() {
		// `useSvelteFlow()` must be called inside `oninit` (not at script top-level):
		// our component is the parent of <SvelteFlow>, not a descendant, so the
		// xyflow context is only established once the flow has initialised. This is
		// the documented pattern — see https://svelteflow.dev/api-reference/svelteflow#oninit
		flowInstance = useSvelteFlow();
		const saved = loadViewport(folderId);
		if (saved) {
			flowInstance?.setViewport(saved);
		} else {
			flowInstance?.fitView({ duration: 200, padding: 0.15 });
		}
	}

	function persistViewport() {
		if (!flowInstance) return;
		const vp = flowInstance.getViewport();
		saveViewportLS(folderId, vp);
	}

	function handleNodeDragStop(_e: any, node?: Node) {
		// SvelteFlow exposes onnodedragstop with (event, draggedNode); fall back to scanning if absent
		const updated = { ...positions };
		for (const n of nodes) {
			updated[n.id] = { x: n.position.x, y: n.position.y };
		}
		positions = updated;
		savePositions(folderId, updated);
	}

	function isValidConnection(connection: Connection): boolean {
		if (!connection.source || !connection.target) return false;
		if (connection.source === connection.target) return false;
		if (edges.some((e) => e.source === connection.source && e.target === connection.target)) {
			return false;
		}
		return true;
	}

	async function patchParentAssets(childId: string, parentIds: string[]): Promise<boolean> {
		try {
			const res = await fetch(`/assets/${childId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ parent_assets: parentIds })
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				const msg =
					(err && (err.parent_assets || err.detail || err.non_field_errors)) ?? 'Update failed';
				toastStore.trigger({
					message: typeof msg === 'string' ? msg : JSON.stringify(msg),
					background: 'preset-tonal-error'
				});
				return false;
			}
			return true;
		} catch (e) {
			toastStore.trigger({
				message: 'Network error updating asset relationship',
				background: 'preset-tonal-error'
			});
			return false;
		}
	}

	function currentParentsOf(childId: string): string[] {
		// Reconstruct from current edges (in-folder) plus any external parents we don't see
		const inFolder = edges.filter((e) => e.target === childId).map((e) => e.source);
		const child = assets.find((a) => a.id === childId);
		const external =
			child?.parent_assets
				?.map((p) => (typeof p === 'object' ? p.id : p))
				.filter((pid) => !knownAssetIds.has(pid)) ?? [];
		return [...inFolder, ...external];
	}

	async function handleConnect(connection: Connection) {
		if (!connection.source || !connection.target) return;
		const newParents = Array.from(
			new Set([...currentParentsOf(connection.target), connection.source])
		);
		const ok = await patchParentAssets(connection.target, newParents);
		if (!ok) {
			// Revert: drop this edge from local state
			edges = edges.filter(
				(e) => !(e.source === connection.source && e.target === connection.target)
			);
		} else {
			toastStore.trigger({ message: 'Link saved', background: 'preset-tonal-success' });
		}
	}

	async function handleDelete({ edges: deletedEdges }: { nodes: Node[]; edges: Edge[] }) {
		// Group removals by target (child) and PATCH once per child
		const byTarget = new Map<string, Set<string>>();
		for (const e of deletedEdges) {
			if (!byTarget.has(e.target)) byTarget.set(e.target, new Set());
			byTarget.get(e.target)!.add(e.source);
		}
		for (const [childId, removedSources] of byTarget) {
			const remaining = currentParentsOf(childId).filter((p) => !removedSources.has(p));
			const ok = await patchParentAssets(childId, remaining);
			if (!ok) {
				// Re-add removed edges to local state. `type: 'asset'` is required —
				// defaultEdgeOptions only applies to edges created via onConnect, not to
				// edges added programmatically here, and without it we'd lose the custom
				// AssetEdge rendering (selected styling, click-to-show delete button).
				for (const src of removedSources) {
					edges = [
						...edges,
						{
							id: `e-${src}-${childId}`,
							source: src,
							target: childId,
							type: 'asset',
							markerEnd: {
								type: MarkerType.ArrowClosed,
								color: 'var(--color-surface-600)'
							}
						}
					];
				}
			}
		}
	}

	function openCreateModal(opts: { dropCoords: XY; parentId?: string }) {
		pendingPlacement = opts.dropCoords;
		pendingParentId = opts.parentId ?? null;
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: assetModel.createForm,
				model: assetModel,
				debug: false,
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: 'Create asset'
		};
		modalStore.trigger(modal);
	}

	let lastPaneClickAt = 0;
	function handlePaneClick({ event }: { event: MouseEvent }) {
		const now = performance.now();
		if (now - lastPaneClickAt < 350) {
			lastPaneClickAt = 0;
			const coords = flowInstance?.screenToFlowPosition({
				x: event.clientX,
				y: event.clientY
			}) ?? { x: 0, y: 0 };
			openCreateModal({ dropCoords: coords });
		} else {
			lastPaneClickAt = now;
		}
	}

	function handleCreateAtCenter() {
		const vp = flowInstance?.getViewport() ?? { x: 0, y: 0, zoom: 1 };
		// place near the visible centre of the canvas in flow coords
		const center = flowInstance?.screenToFlowPosition({
			x: window.innerWidth / 2,
			y: window.innerHeight / 2
		}) ?? { x: 100 - vp.x, y: 100 - vp.y };
		openCreateModal({ dropCoords: center });
	}

	function handleConnectEnd(event: MouseEvent | TouchEvent, connectionState: any) {
		// xyflow Svelte: when a connection ends with no target node, isValid is null
		if (!connectionState || connectionState.isValid !== null) return;
		const fromNodeId = connectionState.fromNode?.id;
		if (!fromNodeId) return;
		const point =
			event instanceof MouseEvent
				? { x: event.clientX, y: event.clientY }
				: { x: event.changedTouches[0].clientX, y: event.changedTouches[0].clientY };
		const coords = flowInstance?.screenToFlowPosition(point) ?? { x: 0, y: 0 };
		openCreateModal({ dropCoords: coords, parentId: fromNodeId });
	}

	async function toggleAssetType(assetId: string): Promise<boolean> {
		// Node data.type is always the raw 'PR' or 'SP' code (set in buildGraph from
		// `is_primary`), so locale-translated values like "Primaire" never reach here.
		const node = nodes.find((n) => n.id === assetId);
		const currentType = (node?.data as any)?.type === 'PR' ? 'PR' : 'SP';
		const nextType = currentType === 'PR' ? 'SP' : 'PR';
		try {
			const res = await fetch(`/assets/${assetId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ type: nextType })
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				const msg = (err && (err.type || err.detail)) ?? 'Type change failed';
				toastStore.trigger({
					message: typeof msg === 'string' ? msg : JSON.stringify(msg),
					background: 'preset-tonal-error'
				});
				return false;
			}
			// AssetWriteSerializer returns the raw code, so a strict equality check
			// surfaces silent server-side rejections.
			const body = await res.json().catch(() => ({}) as any);
			const returned = body?.type;
			if (returned && returned !== nextType) {
				toastStore.trigger({
					message: `Server kept type as "${returned}" — change not applied`,
					background: 'preset-tonal-error'
				});
				return false;
			}
			nodes = nodes.map((n) =>
				n.id === assetId ? { ...n, data: { ...n.data, type: nextType } } : n
			);
			toastStore.trigger({
				message: `Type set to ${nextType === 'PR' ? 'Primary' : 'Support'}`,
				background: 'preset-tonal-success'
			});
			void invalidateAll();
			return true;
		} catch {
			toastStore.trigger({
				message: 'Network error changing asset type',
				background: 'preset-tonal-error'
			});
			return false;
		}
	}

	async function renameAsset(assetId: string, name: string): Promise<boolean> {
		try {
			const res = await fetch(`/assets/${assetId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name })
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				const msg = (err && (err.name || err.detail)) ?? 'Rename failed';
				toastStore.trigger({
					message: typeof msg === 'string' ? msg : JSON.stringify(msg),
					background: 'preset-tonal-error'
				});
				return false;
			}
			// Locally update the visible label so the change shows immediately,
			// then re-fetch to keep the server state authoritative.
			nodes = nodes.map((n) => (n.id === assetId ? { ...n, data: { ...n.data, label: name } } : n));
			void invalidateAll();
			return true;
		} catch {
			toastStore.trigger({
				message: 'Network error renaming asset',
				background: 'preset-tonal-error'
			});
			return false;
		}
	}

	function confirmDeleteAsset(assetId: string, assetName: string) {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: deleteForm,
				id: assetId,
				URLModel: 'assets',
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteModalTitle(),
			body: m.deleteModalMessage({ name: assetName })
		};
		modalStore.trigger(modal);
	}

	setContext('assetBoard', {
		showExternalLinks: (id: string) => {
			const child = assets.find((a) => a.id === id);
			const external =
				child?.parent_assets?.filter((p) => {
					const pid = typeof p === 'object' ? p.id : p;
					return !knownAssetIds.has(pid);
				}) ?? [];
			toastStore.trigger({
				message: `External parent links: ${external.length} (cross-domain editor coming later)`,
				background: 'preset-tonal-warning'
			});
		},
		renameAsset,
		toggleAssetType,
		confirmDeleteAsset,
		deleteEdge: async (source: string, target: string) => {
			// Same logic as ondelete, but for one specific edge selected via the UI button.
			const remaining = currentParentsOf(target).filter((p) => p !== source);
			const ok = await patchParentAssets(target, remaining);
			if (ok) {
				edges = edges.filter((e) => !(e.source === source && e.target === target));
				toastStore.trigger({ message: 'Link removed', background: 'preset-tonal-success' });
			}
		}
	});
</script>

<div class="h-full bg-surface-50 rounded-base overflow-hidden border border-surface-200 relative">
	<SvelteFlow
		bind:nodes
		bind:edges
		{nodeTypes}
		{edgeTypes}
		{isValidConnection}
		onconnect={handleConnect}
		onconnectend={handleConnectEnd}
		onnodedragstop={handleNodeDragStop}
		ondelete={handleDelete}
		onpaneclick={handlePaneClick}
		oninit={handleFlowInit}
		onmoveend={persistViewport}
		zoomOnDoubleClick={false}
		snapGrid={[10, 10]}
		minZoom={0.3}
		proOptions={{ hideAttribution: true }}
		defaultEdgeOptions={{
			type: 'asset',
			markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' }
		}}
	>
		<Background variant={BackgroundVariant.Dots} gap={20} />
		<Controls showLock={false} />
		<MiniMap />
		<Panel position="top-right">
			<button
				type="button"
				class="btn preset-filled-primary-500 text-sm shadow"
				onclick={handleCreateAtCenter}
			>
				<i class="fa-solid fa-plus mr-1"></i>Create asset
			</button>
		</Panel>
		<Panel position="top-left">
			<div
				class="text-xs bg-surface-100 text-surface-700 border border-surface-300 rounded-base shadow-sm max-w-md leading-relaxed"
			>
				<button
					type="button"
					class="w-full flex items-center justify-between px-3 py-2 font-semibold cursor-pointer hover:bg-surface-200 rounded-base"
					aria-expanded={instructionsOpen}
					aria-controls="asset-board-instructions"
					onclick={() => (instructionsOpen = !instructionsOpen)}
				>
					<span>
						<i class="fa-solid fa-info-circle mr-1"></i>Instructions
					</span>
					<i class="fa-solid {instructionsOpen ? 'fa-chevron-up' : 'fa-chevron-down'} text-[10px]"
					></i>
				</button>
				{#if instructionsOpen}
					<div id="asset-board-instructions" class="px-3 pb-2">
						<div class="mb-1 text-surface-600">
							Convention: arrow <span class="font-mono">A → B</span> means
							<em>A depends on B</em> (A is a parent of B).
						</div>
						<ul class="list-disc list-inside space-y-0.5">
							<li>Drag bottom handle of one asset onto another to link it as a parent</li>
							<li>Drag bottom handle onto empty canvas to create a child asset</li>
							<li>Double-click empty canvas to create a free-standing asset</li>
							<li>Double-click a node's name to rename it</li>
							<li>
								Click the <span class="font-semibold">PR/SP</span> pill to toggle the asset type
							</li>
							<li>Hover a node and click the trash icon to delete it (with cascade preview)</li>
							<li>Click a link to select it, then click the × at its midpoint to unlink</li>
							<li>Positions are saved per-domain in this browser only</li>
						</ul>
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
	:global(.svelte-flow .svelte-flow__edge-path) {
		stroke-width: 2;
	}
	:global(.svelte-flow .svelte-flow__edge) {
		cursor: pointer;
	}
	:global(.svelte-flow .svelte-flow__edge:hover .svelte-flow__edge-path) {
		stroke: var(--color-secondary-300);
		stroke-width: 3;
	}
	/* Selected edge: visually obvious so the user can find the delete button. */
	:global(.svelte-flow .svelte-flow__edge.selected .svelte-flow__edge-path),
	:global(.svelte-flow .svelte-flow__edge[aria-selected='true'] .svelte-flow__edge-path) {
		stroke: var(--color-secondary-500);
		stroke-width: 3;
	}
</style>
