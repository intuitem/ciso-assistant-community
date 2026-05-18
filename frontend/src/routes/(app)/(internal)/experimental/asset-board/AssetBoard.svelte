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
	import TrustZoneComponent from './TrustZone.svelte';
	import {
		loadPositions,
		savePositions,
		loadViewport,
		saveViewport as saveViewportLS,
		loadZones,
		saveZones,
		loadMembership,
		saveMembership,
		type XY,
		type TrustZone
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

	const nodeTypes = { asset: AssetNodeComponent, zone: TrustZoneComponent };
	const edgeTypes = { asset: AssetEdgeComponent };

	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let positions = $state<Record<string, XY>>({});
	let zones = $state<TrustZone[]>([]);
	// asset id -> zone id (parent membership, in the xyflow parentId sense)
	let membership = $state<Record<string, string>>({});
	let instructionsOpen = $state(true);
	// drop coordinates + optional parent for the next asset created via the canvas
	let pendingPlacement = $state<XY | null>(null);
	let pendingParentId = $state<string | null>(null);
	let knownAssetIds = $state<Set<string>>(new Set());

	const ZONE_DEFAULT_COLOR = '#3b82f6';
	const ZONE_DEFAULT_W = 320;
	const ZONE_DEFAULT_H = 220;

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

		// Zone nodes come first so child assets render on top.
		const zoneById = new Map(zones.map((z) => [z.id, z]));
		const zoneNodes: Node[] = zones.map((z) => ({
			id: z.id,
			type: 'zone',
			position: { x: z.x, y: z.y },
			data: { label: z.name, color: z.color },
			style: `width: ${z.width}px; height: ${z.height}px;`,
			width: z.width,
			height: z.height,
			draggable: true,
			selectable: true,
			connectable: false,
			deletable: false,
			// Zones must be below assets so the asset header buttons stay clickable
			zIndex: -1
		}));

		const assetNodes: Node[] = assets.map((a, i) => {
			const saved = positions[a.id];
			const absolute = saved ?? defaultPositionFor(i);
			const parentId = membership[a.id];
			const parent = parentId ? zoneById.get(parentId) : undefined;
			// xyflow stores child positions relative to the parent. We persist absolute
			// positions and convert here so the membership and the absolute layout in
			// localStorage stay independent of each other.
			const position = parent ? { x: absolute.x - parent.x, y: absolute.y - parent.y } : absolute;
			const node: Node = {
				id: a.id,
				type: 'asset',
				position,
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
			if (parent) {
				// No `extent: 'parent'` on purpose — we WANT the user to be able to drag an
				// asset out of a zone to remove its membership. reassignMembership runs on
				// drag stop and updates parentId accordingly.
				node.parentId = parentId;
			}
			return node;
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

		nodes = [...zoneNodes, ...assetNodes];
		edges = flowEdges;
		knownAssetIds = inFolderIds;
	}

	// Initial load from localStorage and graph build
	positions = loadPositions(folderId);
	zones = loadZones(folderId);
	membership = loadMembership(folderId);
	// Drop membership for any zone that no longer exists
	let cleanedMembership: Record<string, string> = {};
	const liveZoneIds = new Set(zones.map((z) => z.id));
	for (const [assetId, zoneId] of Object.entries(membership)) {
		if (liveZoneIds.has(zoneId)) cleanedMembership[assetId] = zoneId;
	}
	if (Object.keys(cleanedMembership).length !== Object.keys(membership).length) {
		membership = cleanedMembership;
		saveMembership(folderId, membership);
	}
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

	function handleNodeDragStop(_e: any, draggedNode?: Node) {
		// Live zone positions from the post-drag nodes array — when the user drags a zone,
		// the zone's own n.position is new but its child assets' (relative) positions are
		// unchanged. We compute child absolute positions against this LIVE map, not the
		// stale `zones` state, otherwise children appear to teleport on the next render.
		const liveZonePos: Record<string, XY> = {};
		for (const n of nodes) {
			if (n.type === 'zone') liveZonePos[n.id] = { x: n.position.x, y: n.position.y };
		}

		let zonesChanged = false;
		const updatedZones: TrustZone[] = zones.map((z) => {
			const p = liveZonePos[z.id];
			if (p && (p.x !== z.x || p.y !== z.y)) {
				zonesChanged = true;
				return { ...z, x: p.x, y: p.y };
			}
			return z;
		});

		const updatedPositions: Record<string, XY> = { ...positions };
		for (const n of nodes) {
			if (n.type === 'zone') continue;
			const parentPos = n.parentId ? liveZonePos[n.parentId] : undefined;
			updatedPositions[n.id] = parentPos
				? { x: n.position.x + parentPos.x, y: n.position.y + parentPos.y }
				: { x: n.position.x, y: n.position.y };
		}
		positions = updatedPositions;
		savePositions(folderId, updatedPositions);
		if (zonesChanged) {
			zones = updatedZones;
			saveZones(folderId, zones);
		}

		// If an asset was the one dragged, reassign its membership based on what it overlaps now.
		if (draggedNode && draggedNode.type === 'asset') {
			reassignMembership(draggedNode.id, updatedPositions[draggedNode.id]);
		}
	}

	function reassignMembership(assetId: string, abs: XY) {
		// Find zone containing the asset's top-left corner (good enough for v1).
		// Iterate in reverse so the most-recently-created zone wins on overlap.
		const containing = [...zones].reverse().find((z) => {
			return abs.x >= z.x && abs.x <= z.x + z.width && abs.y >= z.y && abs.y <= z.y + z.height;
		});
		const newZoneId = containing?.id ?? null;
		const currentZoneId = membership[assetId] ?? null;
		if (newZoneId === currentZoneId) return;
		const updated = { ...membership };
		if (newZoneId) updated[assetId] = newZoneId;
		else delete updated[assetId];
		membership = updated;
		saveMembership(folderId, updated);
		buildGraph();
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

	function handleCreateZone() {
		const vp = flowInstance?.getViewport() ?? { x: 0, y: 0, zoom: 1 };
		const center = flowInstance?.screenToFlowPosition({
			x: window.innerWidth / 2,
			y: window.innerHeight / 2
		}) ?? { x: 200 - vp.x, y: 200 - vp.y };
		const zone: TrustZone = {
			id: `zone-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
			name: `Trust zone ${zones.length + 1}`,
			color: ZONE_DEFAULT_COLOR,
			x: center.x - ZONE_DEFAULT_W / 2,
			y: center.y - ZONE_DEFAULT_H / 2,
			width: ZONE_DEFAULT_W,
			height: ZONE_DEFAULT_H
		};
		zones = [...zones, zone];
		saveZones(folderId, zones);
		buildGraph();
	}

	function renameZone(zoneId: string, name: string) {
		zones = zones.map((z) => (z.id === zoneId ? { ...z, name } : z));
		saveZones(folderId, zones);
		buildGraph();
	}

	function recolorZone(zoneId: string, color: string) {
		zones = zones.map((z) => (z.id === zoneId ? { ...z, color } : z));
		saveZones(folderId, zones);
		buildGraph();
	}

	function resizeZone(zoneId: string, width: number, height: number) {
		zones = zones.map((z) => (z.id === zoneId ? { ...z, width, height } : z));
		saveZones(folderId, zones);
		// Reassign membership for every asset — resizing can move zone borders past assets.
		const newMembership: Record<string, string> = {};
		for (const a of assets) {
			const abs = positions[a.id];
			if (!abs) {
				if (membership[a.id]) newMembership[a.id] = membership[a.id];
				continue;
			}
			const containing = [...zones].reverse().find((z) => {
				return abs.x >= z.x && abs.x <= z.x + z.width && abs.y >= z.y && abs.y <= z.y + z.height;
			});
			if (containing) newMembership[a.id] = containing.id;
		}
		membership = newMembership;
		saveMembership(folderId, newMembership);
		buildGraph();
	}

	function deleteZone(zoneId: string) {
		zones = zones.filter((z) => z.id !== zoneId);
		saveZones(folderId, zones);
		const updated = { ...membership };
		for (const [assetId, zid] of Object.entries(updated)) {
			if (zid === zoneId) delete updated[assetId];
		}
		membership = updated;
		saveMembership(folderId, updated);
		buildGraph();
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
		renameZone,
		recolorZone,
		resizeZone,
		deleteZone,
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
			<div class="flex gap-2">
				<button
					type="button"
					class="btn preset-tonal-secondary text-sm shadow"
					onclick={handleCreateZone}
					title="Draw a trust-zone rectangle on the canvas"
				>
					<i class="fa-solid fa-shield-halved mr-1"></i>Add trust zone
				</button>
				<button
					type="button"
					class="btn preset-filled-primary-500 text-sm shadow"
					onclick={handleCreateAtCenter}
				>
					<i class="fa-solid fa-plus mr-1"></i>Create asset
				</button>
			</div>
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
							<li>
								Use <span class="font-semibold">Add trust zone</span> to draw a boundary; drag assets
								inside to nest them, drag back out to remove
							</li>
							<li>Positions, zones and membership are saved per-domain in this browser only</li>
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
