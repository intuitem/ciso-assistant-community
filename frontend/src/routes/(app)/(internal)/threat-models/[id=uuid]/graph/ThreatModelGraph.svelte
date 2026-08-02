<script lang="ts">
	import { m } from '$paraglide/messages';
	import { setContext, untrack } from 'svelte';
	import {
		SvelteFlow,
		useSvelteFlow,
		Controls,
		Background,
		BackgroundVariant,
		MiniMap,
		Panel,
		type Node,
		type Edge,
		type Connection,
		MarkerType
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import TechniqueNodeComponent from './nodes/TechniqueNode.svelte';
	import LaneNodeComponent from './nodes/LaneNode.svelte';
	import TechniquePalette from './TechniquePalette.svelte';
	import type { PaletteTechnique } from './TechniquePalette.svelte';

	interface GraphTactic {
		id: string;
		ref_id: string;
		name: string;
	}

	interface GraphNode {
		/** `techniqueId:tacticId` — the same technique in two tactics is two nodes */
		id: string;
		technique: string;
		ref_id: string;
		name: string;
		parent_name: string | null;
		tactic: string;
		label: string;
		position_x: number;
		position_y: number;
	}

	interface Props {
		threatModelId: string;
		tactics: GraphTactic[];
		graphNodes: GraphNode[];
		graphEdges: { source: string; target: string }[];
		graphColumns?: Record<string, { x: number; y: number; width: number; height: number }>;
		paletteTechniques: PaletteTechnique[];
		readonly?: boolean;
	}

	let {
		threatModelId,
		tactics,
		graphNodes,
		graphEdges,
		graphColumns = {},
		paletteTechniques,
		readonly = false
	}: Props = $props();

	const LANE_GAP = 320;
	const LANE_WIDTH = 260;
	const LANE_HEIGHT = 480;
	const NODE_GAP_Y = 80;
	const NODE_PADDING_X = 35;
	const NODE_PADDING_Y = 70;

	const laneId = (tacticId: string) => `lane-${tacticId}`;
	const tacticOf = (laneNodeId: string) => laneNodeId.replace(/^lane-/, '');

	let nodes = $state.raw<Node[]>([]);
	let edges = $state.raw<Edge[]>([]);
	let dirty = $state(false);
	let saving = $state(false);
	let errorMessage = $state('');
	let dragOverLane = $state<string | null>(null);
	// tactics of the technique currently being dragged, null when idle
	let dragTactics = $state<string[] | null>(null);
	let showAllLanes = $state(false);

	const { screenToFlowPosition } = useSvelteFlow();

	// `techniqueId:tacticId` keys, so the palette can show a technique as placed
	// in one tactic while still offering it in another
	const placedIds = $derived(
		new Set(nodes.filter((node) => node.type === 'technique').map((node) => node.id))
	);

	setContext('threatModelEditor', {
		get dragOverLane() {
			return dragOverLane;
		},
		get dragTactics() {
			return dragTactics;
		},
		get readonly() {
			return readonly;
		},
		deleteNode: (id: string) => removeNode(id),
		markDirty: () => (dirty = true)
	});

	function countIn(laneNodeId: string, current: Node[]): number {
		return current.filter((node) => node.type === 'technique' && node.parentId === laneNodeId)
			.length;
	}

	function buildLaneNodes(current: Node[]): Node[] {
		return tactics.map((tactic, index) => {
			const id = laneId(tactic.id);
			const saved = graphColumns[id];
			return {
				id,
				type: 'lane',
				position: saved ? { x: saved.x, y: saved.y } : { x: index * LANE_GAP, y: 0 },
				style: `width: ${saved?.width ?? LANE_WIDTH}px; height: ${saved?.height ?? LANE_HEIGHT}px;`,
				data: { name: tactic.name, refId: tactic.ref_id, count: countIn(id, current) },
				selectable: true,
				draggable: false,
				deletable: false,
				connectable: false
			} as Node;
		});
	}

	function initGraph() {
		const perLane: Record<string, number> = {};
		const techniqueNodes: Node[] = [];

		for (const node of graphNodes) {
			if (!node.tactic) continue;
			const parentId = laneId(node.tactic);
			const index = perLane[parentId] ?? 0;
			const placed = node.position_x !== 0 || node.position_y !== 0;
			techniqueNodes.push({
				id: node.id,
				type: 'technique',
				position: placed
					? { x: node.position_x, y: node.position_y }
					: { x: NODE_PADDING_X, y: NODE_PADDING_Y + index * NODE_GAP_Y },
				parentId,
				extent: 'parent',
				draggable: !readonly,
				deletable: !readonly,
				connectable: !readonly,
				data: {
					label: node.label || node.name,
					// the stored label, kept apart from the fallback so saving cannot
					// overwrite it with the technique name
					customLabel: node.label,
					refId: node.ref_id,
					parentName: node.parent_name
				}
			} as Node);
			perLane[parentId] = index + 1;
		}

		dirty = false;
		nodes = [...buildLaneNodes(techniqueNodes), ...techniqueNodes];
		edges = graphEdges.map((edge) => ({
			id: `e-${edge.source}-${edge.target}`,
			source: edge.source,
			target: edge.target,
			markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' },
			style: 'stroke: var(--color-surface-500); stroke-width: 2;'
		}));
	}

	initGraph();

	// update the badge in place — rebuilding lane nodes would discard whatever the
	// analyst resized or dragged them to
	function refreshLaneCounts() {
		nodes = nodes.map((node) =>
			node.type === 'lane'
				? { ...node, data: { ...node.data, count: countIn(node.id, nodes) } }
				: node
		);
	}

	// Empty tactics are noise: a model touching 5 of 15 tactics should show 5
	// columns. Hidden rather than removed, so geometry survives the toggle — and
	// a drag reveals everything so you can always reach an empty lane.
	//
	// This derives a STRING, not a Set. The effect below writes `nodes`, which
	// re-runs this; a fresh Set is a new reference every time and would loop
	// forever, while an unchanged string compares equal and stops the cascade.
	const hiddenLaneKey = $derived(
		showAllLanes || dragTactics
			? ''
			: nodes
					.filter((node) => node.type === 'lane' && countIn(node.id, nodes) === 0)
					.map((node) => node.id)
					.sort()
					.join(',')
	);

	$effect(() => {
		const hidden = new Set(hiddenLaneKey ? hiddenLaneKey.split(',') : []);
		untrack(() => {
			// second guard: never assign a new array unless something actually changed
			let changed = false;
			const next = nodes.map((node) => {
				const target = node.type === 'lane' ? node.id : node.parentId;
				const shouldHide = target ? hidden.has(target) : false;
				if (Boolean(node.hidden) === shouldHide) return node;
				changed = true;
				return { ...node, hidden: shouldHide };
			});
			if (changed) nodes = next;
		});
	});

	const emptyLaneCount = $derived(
		nodes.filter((node) => node.type === 'lane' && countIn(node.id, nodes) === 0).length
	);

	function removeNode(id: string) {
		nodes = nodes.filter((node) => node.id !== id);
		edges = edges.filter((edge) => edge.source !== id && edge.target !== id);
		dirty = true;
		refreshLaneCounts();
	}

	// deliberately permissive: cycles and backward edges are legitimate in an
	// attack flow, so the only rules are no self-loop and no duplicate
	function isValidConnection(connection: Connection): boolean {
		if (connection.source === connection.target) return false;
		return !edges.some(
			(edge) => edge.source === connection.source && edge.target === connection.target
		);
	}

	function handleConnect() {
		dirty = true;
	}

	function handleDelete() {
		dirty = true;
		refreshLaneCounts();
	}

	function laneAt(clientX: number, clientY: number): Node | undefined {
		const point = screenToFlowPosition({ x: clientX, y: clientY });
		return nodes.find((node) => {
			if (node.type !== 'lane') return false;
			const width = node.measured?.width ?? LANE_WIDTH;
			const height = node.measured?.height ?? LANE_HEIGHT;
			return (
				point.x >= node.position.x &&
				point.x <= node.position.x + width &&
				point.y >= node.position.y &&
				point.y <= node.position.y + height
			);
		});
	}

	function laneAccepts(laneNodeId: string, tactics: string[] | null): boolean {
		if (!tactics) return true;
		return tactics.includes(tacticOf(laneNodeId));
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		const lane = laneAt(event.clientX, event.clientY);
		const allowed = lane ? laneAccepts(lane.id, dragTactics) : false;
		if (event.dataTransfer) event.dataTransfer.dropEffect = allowed ? 'move' : 'none';
		dragOverLane = allowed ? (lane?.id ?? null) : null;
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		const lane = laneAt(event.clientX, event.clientY);
		dragOverLane = null;
		dragTactics = null;
		if (!lane || !event.dataTransfer) return;

		const raw = event.dataTransfer.getData('application/json');
		if (!raw) return;
		const technique = JSON.parse(raw) as {
			id: string;
			ref_id: string;
			name: string;
			tactics: string[];
			parentName?: string | null;
		};
		const cellId = `${technique.id}:${tacticOf(lane.id)}`;
		if (placedIds.has(cellId)) return;
		// the backend rejects a technique in a tactic it does not belong to, so
		// refuse the drop rather than let it fail on save
		if (!laneAccepts(lane.id, technique.tactics ?? null)) return;

		const point = screenToFlowPosition({ x: event.clientX, y: event.clientY });
		nodes = [
			...nodes,
			{
				id: cellId,
				type: 'technique',
				position: { x: point.x - lane.position.x, y: point.y - lane.position.y },
				parentId: lane.id,
				extent: 'parent',
				draggable: true,
				deletable: true,
				connectable: true,
				data: {
					label: technique.name,
					customLabel: '',
					refId: technique.ref_id,
					parentName: technique.parentName ?? null
				}
			} as Node
		];
		dirty = true;
		refreshLaneCounts();
	}

	// Draft a sequence from the tactic order: every node in an occupied lane feeds
	// every node in the next occupied one. Additive — existing edges are kept, and
	// nothing is removed, so it is a starting point to prune rather than a layout.
	function autoLink() {
		const order = tactics.map((tactic) => laneId(tactic.id));
		const occupied = order
			.map((id) => ({
				id,
				members: nodes.filter((node) => node.type === 'technique' && node.parentId === id)
			}))
			.filter((lane) => lane.members.length > 0);

		const existing = new Set(edges.map((edge) => `${edge.source}->${edge.target}`));
		const added: Edge[] = [];

		for (let i = 0; i < occupied.length - 1; i++) {
			for (const source of occupied[i].members) {
				for (const target of occupied[i + 1].members) {
					const key = `${source.id}->${target.id}`;
					if (existing.has(key)) continue;
					existing.add(key);
					added.push({
						id: `e-${source.id}-${target.id}`,
						source: source.id,
						target: target.id,
						markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' },
						style: 'stroke: var(--color-surface-500); stroke-width: 2;'
					});
				}
			}
		}

		if (!added.length) return;
		edges = [...edges, ...added];
		dirty = true;
	}

	function buildPayload() {
		const laneGeometry: Record<string, { x: number; y: number; width: number; height: number }> =
			{};
		for (const node of nodes) {
			if (node.type !== 'lane') continue;
			laneGeometry[node.id] = {
				x: node.position.x,
				y: node.position.y,
				width: node.measured?.width ?? LANE_WIDTH,
				height: node.measured?.height ?? LANE_HEIGHT
			};
		}

		return {
			nodes: nodes
				.filter((node) => node.type === 'technique')
				.map((node) => ({
					id: node.id,
					label: (node.data as any).customLabel ?? '',
					position_x: node.position.x,
					position_y: node.position.y
				})),
			edges: edges.map((edge) => ({ source: edge.source, target: edge.target })),
			graph_columns: laneGeometry
		};
	}

	async function save() {
		saving = true;
		errorMessage = '';
		try {
			const res = await fetch(`/threat-models/${threatModelId}/save-graph`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(buildPayload())
			});
			const payload = await res.json().catch(() => ({}));
			if (res.ok) {
				dirty = false;
			} else {
				errorMessage = (payload.errors ?? [m.anErrorOccurred()]).join(' ');
			}
		} catch {
			errorMessage = m.anErrorOccurred();
		} finally {
			saving = false;
		}
	}
</script>

<div class="flex h-full w-full overflow-hidden">
	{#if !readonly}
		<TechniquePalette
			lanes={tactics}
			techniques={paletteTechniques}
			{placedIds}
			onDragStateChange={(tactics) => (dragTactics = tactics)}
		/>
	{/if}

	<div class="relative flex-1" ondragover={handleDragOver} ondrop={handleDrop} role="application">
		<SvelteFlow
			bind:nodes
			bind:edges
			nodeTypes={{ technique: TechniqueNodeComponent, lane: LaneNodeComponent }}
			{isValidConnection}
			onconnect={handleConnect}
			ondelete={handleDelete}
			onnodedragstop={() => (dirty = true)}
			nodesDraggable={!readonly}
			nodesConnectable={!readonly}
			elementsSelectable={!readonly}
			snapGrid={[10, 10]}
			minZoom={0.2}
			fitView
			proOptions={{ hideAttribution: true }}
			defaultEdgeOptions={{
				markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' },
				style: 'stroke: var(--color-surface-500); stroke-width: 2;'
			}}
		>
			<Background variant={BackgroundVariant.Dots} gap={20} />
			{#if !readonly}
				<Panel position="top-left">
					<div class="flex items-center gap-2">
						<button
							type="button"
							class="btn btn-sm preset-tonal-surface"
							onclick={autoLink}
							title={m.autoLinkHelp()}
						>
							<i class="fa-solid fa-diagram-project mr-1"></i>{m.autoLink()}
						</button>
						{#if emptyLaneCount}
							<button
								type="button"
								class="btn btn-sm preset-tonal-surface"
								onclick={() => (showAllLanes = !showAllLanes)}
								aria-pressed={showAllLanes}
							>
								<i class="fa-solid fa-{showAllLanes ? 'eye-slash' : 'eye'} mr-1"></i>
								{showAllLanes ? m.hideEmptyTactics() : m.showAllTactics({ count: emptyLaneCount })}
							</button>
						{/if}
					</div>
				</Panel>
				<Panel position="top-right">
					<div class="flex items-center gap-2">
						{#if errorMessage}
							<span class="text-xs text-error-500 max-w-sm">{errorMessage}</span>
						{/if}
						{#if dirty}
							<span class="text-xs text-warning-500 flex items-center gap-1">
								<i class="fa-solid fa-circle text-[6px]"></i>
								{m.unsavedChanges()}
							</span>
							<button type="button" class="btn preset-tonal text-sm" onclick={initGraph}>
								<i class="fa-solid fa-rotate-left mr-1"></i>
								{m.discardChanges()}
							</button>
						{/if}
						<button
							type="button"
							class="btn preset-filled-primary-500 text-sm"
							disabled={!dirty || saving}
							onclick={save}
						>
							{#if saving}
								<i class="fa-solid fa-spinner fa-spin mr-1"></i>
							{:else}
								<i class="fa-solid fa-save mr-1"></i>
							{/if}
							{m.save()}
						</button>
					</div>
				</Panel>
			{/if}
			<Controls showLock={false} />
			<MiniMap />
		</SvelteFlow>
	</div>
</div>

<style>
	:global(.svelte-flow) {
		--xy-node-border-radius: var(--radius-base);
		--xy-edge-stroke: var(--color-surface-500);
		--xy-background-color: var(--color-surface-50);
		--xy-background-pattern-color: var(--color-surface-300);
	}
	:global(.dark .svelte-flow) {
		--xy-background-color: var(--color-surface-950);
		--xy-background-pattern-color: var(--color-surface-800);
		--xy-controls-button-background-color: var(--color-surface-800);
		--xy-controls-button-background-color-hover: var(--color-surface-700);
		--xy-controls-button-color: var(--color-surface-100);
		--xy-controls-button-color-hover: var(--color-surface-50);
		--xy-controls-button-border-color: var(--color-surface-700);
		--xy-minimap-background-color: var(--color-surface-900);
		--xy-minimap-mask-background-color: var(--color-surface-950);
		--xy-minimap-node-background-color: var(--color-surface-600);
	}
	:global(.svelte-flow .svelte-flow__edge-path) {
		stroke-width: 2;
	}
</style>
