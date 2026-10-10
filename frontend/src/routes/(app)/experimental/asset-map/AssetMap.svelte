<script lang="ts">
	import { setContext, tick, untrack } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import {
		SvelteFlow,
		useSvelteFlow,
		Controls,
		ControlButton,
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

	import MapNode from './MapNode.svelte';
	import AssetEdge from '$lib/components/AssetGraph/AssetEdge.svelte';
	import { computeLayout } from '$lib/components/AssetGraph/layout';
	import { createLinkWriter } from '$lib/components/AssetGraph/links';
	import { createPickerForm } from '$lib/components/AssetGraph/picker';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { fetchAllByIds } from '$lib/utils/pagination';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import { resolvedTheme } from '$lib/utils/theme';

	interface GraphNode {
		id: string;
		hidden: boolean;
		hops: number;
		side: string;
		omitted: number;
		elsewhere?: number;
		name?: string;
		ref_id?: string | null;
		type?: string;
		folder?: { id: string; str: string; path: string };
	}

	interface Graph {
		focus: string;
		mode: string;
		truncated: boolean;
		nodes: GraphNode[];
		edges: { source: string; target: string }[];
	}

	interface Props {
		graph: Graph;
		assetModel: any;
		onRefocus: (id: string) => void;
		onExpand: (id: string) => void;
		onReveal: (...ids: string[]) => void;
	}

	let { graph, assetModel, onRefocus, onExpand, onReveal }: Props = $props();

	type XY = { x: number; y: number };

	const toastStore = getToastStore();
	const modalStore = getModalStore();
	const { updateParents } = createLinkWriter((message) =>
		toastStore.trigger({ message, background: 'preset-tonal-error' })
	);

	const nodeTypes = { asset: MapNode };
	const edgeTypes = { asset: AssetEdge };
	const marker = { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' };
	const CLEAR_X = 240;
	const CLEAR_Y = 90;

	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let positions: Record<string, XY> = {};
	let extras = $state<GraphNode[]>([]);
	let pendingDrop: { near: string; at: XY } | null = null;
	let laidOut = false;
	let helpOpen = $state(false);
	let searchOpen = $state(false);
	const linkPicker = createPickerForm('asset');
	let flow: ReturnType<typeof useSvelteFlow> | null = null;

	function placeNewNode(id: string, links: { source: string; target: string }[]): XY {
		if (
			pendingDrop &&
			links.some((e) => e.source === pendingDrop!.near || e.target === pendingDrop!.near)
		) {
			return pendingDrop.at;
		}
		for (const e of links) {
			if (e.target === id && positions[e.source]) {
				return { x: positions[e.source].x, y: positions[e.source].y + 130 };
			}
			if (e.source === id && positions[e.target]) {
				return { x: positions[e.target].x, y: positions[e.target].y - 130 };
			}
		}
		const xs = Object.values(positions).map((p) => p.x);
		return { x: (xs.length ? Math.max(...xs) : 0) + 260, y: 0 };
	}

	function build() {
		const focusFolder = graph.nodes.find((n) => n.id === graph.focus)?.folder?.id;
		const inGraph = new Set(graph.nodes.map((n) => n.id));
		extras = extras.filter((x) => !inGraph.has(x.id));
		const all = [...graph.nodes, ...extras];
		const byId = new Map(all.map((n) => [n.id, n]));

		const created: string[] = [];
		for (const n of all) {
			if (!positions[n.id]) created.push(n.id);
		}
		if (laidOut) {
			for (const id of created) {
				const links = graph.edges.filter((e) => e.source === id || e.target === id);
				let spot = placeNewNode(id, links);
				while (
					Object.values(positions).some(
						(p) => Math.abs(p.x - spot.x) < CLEAR_X && Math.abs(p.y - spot.y) < CLEAR_Y
					)
				) {
					spot = { x: spot.x + CLEAR_X, y: spot.y };
				}
				positions[id] = spot;
			}
			pendingDrop = null;
		}

		nodes = all.map((n) => ({
			id: n.id,
			type: 'asset',
			position: positions[n.id] ?? { x: 0, y: 0 },
			data: {
				label: n.name,
				refId: n.ref_id ?? '',
				type: n.type,
				folderId: n.folder?.id,
				folderName: n.folder?.str,
				folderPath: n.folder?.path,
				hidden: n.hidden,
				focus: n.id === graph.focus,
				local: n.folder?.id === focusFolder,
				omitted: n.omitted,
				elsewhere: n.elsewhere
			},
			deletable: false,
			connectable: !n.hidden
		}));

		edges = graph.edges.map((e) => {
			const s = byId.get(e.source);
			const t = byId.get(e.target);
			const locked = !!(s?.hidden || t?.hidden);
			return {
				id: `e-${e.source}-${e.target}`,
				source: e.source,
				target: e.target,
				type: 'asset',
				data: { crossDomain: locked || s?.folder?.id !== t?.folder?.id },
				selectable: !locked,
				deletable: !locked,
				markerEnd: marker
			};
		});

		if (!laidOut) {
			const initial = computeLayout(nodes, edges);
			nodes = nodes.map((node) => ({ ...node, position: initial.get(node.id) ?? node.position }));
			positions = Object.fromEntries(nodes.map((n) => [n.id, { ...n.position }]));
			laidOut = true;
		}
	}

	build();

	$effect(() => {
		void graph;
		untrack(build);
	});

	function fit() {
		void tick().then(() =>
			requestAnimationFrame(() =>
				requestAnimationFrame(() => flow?.fitView({ duration: 300, padding: 0.15, maxZoom: 1 }))
			)
		);
	}

	function applyLayout() {
		const laidOut = computeLayout(nodes, edges);
		nodes = nodes.map((node) => {
			const position = laidOut.get(node.id);
			return position ? { ...node, position } : node;
		});
		positions = Object.fromEntries(nodes.map((n) => [n.id, { ...n.position }]));
		fit();
	}

	function handleDragStop() {
		for (const n of nodes) positions[n.id] = { ...n.position };
	}

	function isHidden(id: string) {
		return !!nodes.find((n) => n.id === id)?.data?.hidden;
	}

	function isValidConnection(c: Connection | Edge): boolean {
		if (!c.source || !c.target || c.source === c.target) return false;
		if (isHidden(c.source) || isHidden(c.target)) return false;
		return !edges.some((e) => e.source === c.source && e.target === c.target);
	}

	async function handleConnect(c: Connection) {
		const source = c.source;
		const ok = await updateParents(c.target, (parents) =>
			Array.from(new Set([...parents, source]))
		);
		if (ok) {
			toastStore.trigger({ message: 'Link saved', background: 'preset-tonal-success' });
			onReveal(source, c.target);
		} else {
			edges = edges.filter((e) => !(e.source === c.source && e.target === c.target));
		}
	}

	async function unlink(source: string, target: string) {
		const ok = await updateParents(target, (parents) => parents.filter((p) => p !== source));
		if (ok) {
			edges = edges.filter((e) => !(e.source === source && e.target === target));
			toastStore.trigger({ message: 'Link removed', background: 'preset-tonal-success' });
			void invalidateAll();
		}
	}

	async function handleDelete({ edges: removed }: { nodes: Node[]; edges: Edge[] }) {
		for (const e of removed) await unlink(e.source, e.target);
	}

	const handleConnectEnd: OnConnectEnd = (event, state) => {
		if (!state || state.isValid !== null || !state.fromNode) return;
		const from = nodes.find((n) => n.id === state.fromNode!.id);
		if (!from || from.data?.hidden) return;
		const point =
			'changedTouches' in event
				? { x: event.changedTouches[0].clientX, y: event.changedTouches[0].clientY }
				: { x: event.clientX, y: event.clientY };
		pendingDrop = { near: from.id, at: flow?.screenToFlowPosition(point) ?? { x: 0, y: 0 } };
		const asParent = state.fromHandle?.type === 'target';
		const form = {
			...assetModel.createForm,
			data: {
				...assetModel.createForm.data,
				folder: from.data?.folderId,
				type: asParent ? 'PR' : 'SP',
				...(asParent ? { support_assets: [from.id] } : { parent_assets: [from.id] })
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: {
				ref: CreateModal,
				props: { form, model: assetModel, debug: false, invalidateAll: true }
			},
			title: asParent ? 'Create a parent asset' : 'Create a supporting asset',
			response: (created: boolean) => {
				if (created) onReveal(from.id);
			}
		};
		modalStore.trigger(modal);
	};

	function centerOn(id: string) {
		const at = positions[id];
		if (at) flow?.setCenter(at.x + 100, at.y + 30, { zoom: flow.getZoom(), duration: 300 });
	}

	async function pickExisting(id: string | null) {
		if (!id) return;
		linkPicker.clear();
		searchOpen = false;
		if (nodes.some((n) => n.id === id)) {
			centerOn(id);
			return;
		}
		const [asset] = await fetchAllByIds<any>(fetch, '/assets', [id]).catch(() => []);
		if (asset) addExisting(asset);
	}

	function addExisting(asset: any) {
		const folder = typeof asset.folder === 'object' && asset.folder ? asset.folder : null;
		const center = flow?.screenToFlowPosition({
			x: window.innerWidth / 2,
			y: window.innerHeight / 2
		}) ?? { x: 0, y: 0 };
		const xs = Object.values(positions).map((p) => p.x);
		positions[asset.id] = { x: (xs.length ? Math.max(...xs) : 0) + 260, y: center.y };
		extras = [
			...extras,
			{
				id: asset.id,
				hidden: false,
				hops: -1,
				side: 'any',
				omitted: 0,
				name: asset.name,
				ref_id: asset.ref_id,
				type: asset.is_primary ? 'PR' : 'SP',
				folder: folder ? { id: folder.id, str: folder.str, path: folder.str } : undefined
			}
		];
		build();
		centerOn(asset.id);
	}

	setContext('assetGraph', {
		refocus: onRefocus,
		expand: onExpand,
		reveal: onReveal,
		deleteEdge: unlink
	});
</script>

<div
	class="h-full bg-surface-50-950 rounded-base overflow-hidden border border-surface-200-800 relative"
>
	<SvelteFlow
		bind:nodes
		bind:edges
		colorMode={$resolvedTheme}
		{nodeTypes}
		{edgeTypes}
		{isValidConnection}
		onconnect={handleConnect}
		onconnectend={handleConnectEnd}
		onnodedragstop={handleDragStop}
		ondelete={handleDelete}
		oninit={() => (flow = useSvelteFlow())}
		fitView
		fitViewOptions={{ padding: 0.15, maxZoom: 1 }}
		zoomOnDoubleClick={false}
		minZoom={0.2}
		proOptions={{ hideAttribution: true }}
		defaultEdgeOptions={{ type: 'asset', markerEnd: marker }}
	>
		<Background variant={BackgroundVariant.Dots} gap={20} />
		<Controls showLock={false}>
			<ControlButton onclick={applyLayout} title={m.tidyUp()} aria-label={m.tidyUp()}>
				<i class="fa-solid fa-wand-magic-sparkles"></i>
			</ControlButton>
		</Controls>
		<MiniMap />
		<Panel position="top-right">
			<div class="flex flex-col items-end gap-2">
				<button
					type="button"
					class="btn preset-tonal-warning text-sm shadow"
					onclick={() => (searchOpen = !searchOpen)}
				>
					<i class="fa-solid fa-link mr-1"></i>Link existing asset
				</button>
				{#if searchOpen}
					<div
						class="w-80 bg-surface-50-950 border border-surface-300-700 rounded-base shadow-lg p-2"
					>
						<AutocompleteSelect
							form={linkPicker.form}
							field="asset"
							optionsEndpoint="assets"
							optionsLabelField="auto"
							optionsInfoFields={{ fields: [{ field: 'type' }], classes: 'text-blue-500' }}
							optionsExtraFields={[['folder', 'str']]}
							lazy
							portalDropdown
							placeholder="Search assets in any domain…"
							onChange={pickExisting}
						/>
					</div>
				{/if}
			</div>
		</Panel>
		<Panel position="top-left">
			<div
				class="text-xs bg-surface-100-900 text-surface-700-300 border border-surface-300-700 rounded-base shadow-sm max-w-sm leading-relaxed"
			>
				<button
					type="button"
					class="w-full flex items-center justify-between gap-3 px-3 py-2 font-semibold cursor-pointer hover:bg-surface-200-800 rounded-base"
					aria-expanded={helpOpen}
					onclick={() => (helpOpen = !helpOpen)}
				>
					<span><i class="fa-solid fa-info-circle mr-1"></i>Instructions</span>
					<i class="fa-solid {helpOpen ? 'fa-chevron-up' : 'fa-chevron-down'} text-[10px]"></i>
				</button>
				{#if helpOpen}
					<ul class="list-disc list-inside space-y-0.5 px-3 pb-2">
						<li>Arrow <span class="font-mono">A → B</span>: A depends on B</li>
						<li>Dashed nodes live in another domain than the focus</li>
						<li>
							Double-click a node, or use its crosshairs, to make it the focus; the header keeps the
							trail
						</li>
						<li>Click <span class="font-semibold">+N</span> to draw links not shown yet</li>
						<li>
							A grey <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i> count marks links
							outside the chain, such as another parent of a supporting asset; click it to draw them
						</li>
						<li>Drag between handles to link; select a link and click × to unlink</li>
						<li>
							Drag a bottom handle to empty space to create a supporting asset, a top one for a
							parent
						</li>
						<li>Positions last for this session; the wand re-arranges everything</li>
					</ul>
				{/if}
			</div>
		</Panel>
		{#if graph.truncated}
			<Panel position="bottom-center">
				<div
					class="text-xs px-3 py-1.5 rounded-base border border-warning-300 bg-warning-50-950 text-warning-800 shadow-sm"
				>
					Large graph: only the closest assets are drawn. Use +N to go further.
				</div>
			</Panel>
		{/if}
	</SvelteFlow>
</div>
