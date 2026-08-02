<script lang="ts">
	import { m } from '$paraglide/messages';
	import { setContext, tick, untrack } from 'svelte';
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
	import OperatorNodeComponent from './nodes/OperatorNode.svelte';
	import TechniquePalette from './TechniquePalette.svelte';
	import NodeInspector from './NodeInspector.svelte';
	import type { PaletteTechnique } from './TechniquePalette.svelte';

	interface GraphTactic {
		id: string;
		ref_id: string;
		name: string;
	}

	interface GraphNode {
		id: string;
		kind: 'technique' | 'operator' | 'custom';
		operator: 'AND' | 'OR' | null;
		technique: string | null;
		ref_id: string | null;
		name: string | null;
		parent_name: string | null;
		tactic: string | null;
		label: string;
		description: string;
		is_highlighted: boolean;
		assets: string[];
		applied_controls: string[];
		vulnerabilities: string[];
		properties: Record<string, unknown>;
		position_x: number;
		position_y: number;
	}

	interface Props {
		threatModelId: string;
		tactics: GraphTactic[];
		graphNodes: GraphNode[];
		graphEdges: { source: string; target: string }[];
		graphColumns?: Record<string, { width: number; height: number }>;
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

	const LANE_GAP_X = 60;
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
	let selectedNodeId = $state<string | null>(null);

	const { screenToFlowPosition } = useSvelteFlow();

	// `techniqueId:tacticId`: placed in one tactic, still offered in another
	const placedIds = $derived(
		new Set(
			nodes
				.filter((node) => node.type === 'technique')
				.map((node) => `${(node.data as any).technique}:${(node.data as any).tactic}`)
		)
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
		toggleOperator: (id: string) => toggleOperator(id),
		markDirty: () => (dirty = true)
	});

	function nodeData(node: GraphNode) {
		return {
			kind: node.kind,
			operator: node.operator,
			technique: node.technique,
			tactic: node.tactic,
			label: node.label || node.name || '',
			customLabel: node.label,
			refId: node.ref_id,
			parentName: node.parent_name,
			description: node.description,
			isHighlighted: node.is_highlighted,
			assets: node.assets,
			appliedControls: node.applied_controls,
			vulnerabilities: node.vulnerabilities,
			properties: node.properties
		};
	}

	function countIn(laneNodeId: string, current: Node[]): number {
		return current.filter((node) => node.type === 'technique' && node.parentId === laneNodeId)
			.length;
	}

	const laneWidth = (id: string) => graphColumns[id]?.width ?? LANE_WIDTH;

	function buildLaneNodes(current: Node[]): Node[] {
		return tactics.map((tactic) => {
			const id = laneId(tactic.id);
			const saved = graphColumns[id];
			return {
				id,
				type: 'lane',
				// x is assigned by layoutLanes(); lanes are not user-positioned
				position: { x: 0, y: 0 },
				style: `width: ${laneWidth(id)}px; height: ${saved?.height ?? LANE_HEIGHT}px;`,
				data: { name: tactic.name, refId: tactic.ref_id, count: countIn(id, current) },
				selectable: true,
				draggable: false,
				deletable: false,
				connectable: false
			} as Node;
		});
	}

	// lane x is derived, never stored: lanes resize but never move
	function layoutLanes(current: Node[], hidden: Set<string>): Node[] {
		let x = 0;
		const positions = new Map<string, number>();
		for (const tactic of tactics) {
			const id = laneId(tactic.id);
			if (hidden.has(id)) continue;
			positions.set(id, x);
			x += laneWidth(id) + LANE_GAP_X;
		}
		// same reference when nothing moved: the caller's effect writes `nodes`
		let moved = false;
		const next = current.map((node) => {
			if (node.type !== 'lane') return node;
			const x = positions.get(node.id);
			if (x === undefined || node.position.x === x) return node;
			moved = true;
			return { ...node, position: { x, y: 0 } };
		});
		return moved ? next : current;
	}

	function initGraph() {
		const perLane: Record<string, number> = {};
		const flowNodes: Node[] = [];

		for (const node of graphNodes) {
			const parentId = node.tactic ? laneId(node.tactic) : undefined;
			const index = parentId ? (perLane[parentId] ?? 0) : 0;
			const placed = node.position_x !== 0 || node.position_y !== 0;
			flowNodes.push({
				id: node.id,
				type: node.kind === 'operator' ? 'operator' : 'technique',
				position: placed
					? { x: node.position_x, y: node.position_y }
					: { x: NODE_PADDING_X, y: NODE_PADDING_Y + index * NODE_GAP_Y },
				...(parentId ? { parentId, extent: 'parent' as const } : {}),
				draggable: !readonly,
				deletable: !readonly,
				connectable: !readonly,
				data: nodeData(node)
			} as Node);
			if (parentId) perLane[parentId] = index + 1;
		}

		dirty = false;
		errorMessage = '';
		nodes = layoutLanes([...buildLaneNodes(flowNodes), ...flowNodes], new Set());
		edges = graphEdges.map((edge) => ({
			id: `e-${edge.source}-${edge.target}`,
			source: edge.source,
			target: edge.target,
			markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' },
			style: 'stroke: var(--color-surface-500); stroke-width: 2;'
		}));
	}

	initGraph();

	// in place: rebuilding lane nodes would discard analyst resizing
	function refreshLaneCounts() {
		nodes = nodes.map((node) =>
			node.type === 'lane'
				? { ...node, data: { ...node.data, count: countIn(node.id, nodes) } }
				: node
		);
	}

	// hidden, not removed, so geometry survives the toggle; a drag reveals all.
	// a STRING, not a Set: the effect below writes `nodes` and re-runs this, and a
	// fresh reference would loop forever
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
			const base = changed ? next : nodes;
			const laid = layoutLanes(base, hidden);
			if (laid !== nodes) nodes = laid;
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

	const selectedNode = $derived(
		nodes.find((node) => node.id === selectedNodeId && node.type !== 'lane') ?? null
	);

	function patchSelected(patch: Record<string, unknown>) {
		if (!selectedNodeId) return;
		nodes = nodes.map((node) =>
			node.id === selectedNodeId ? { ...node, data: { ...node.data, ...patch } } : node
		);
		dirty = true;
	}

	function addCustomNode() {
		const lane = nodes.find((node) => node.type === 'lane' && !node.hidden);
		const offset = lane ? countIn(lane.id, nodes) : nodes.filter((n) => n.type !== 'lane').length;
		nodes = [
			...nodes,
			{
				id: crypto.randomUUID(),
				type: 'technique',
				position: { x: NODE_PADDING_X, y: NODE_PADDING_Y + offset * NODE_GAP_Y },
				...(lane ? { parentId: lane.id, extent: 'parent' as const } : {}),
				draggable: true,
				deletable: true,
				connectable: true,
				data: {
					kind: 'custom',
					technique: null,
					tactic: lane ? tacticOf(lane.id) : null,
					label: '',
					customLabel: '',
					refId: null,
					parentName: null,
					description: '',
					isHighlighted: false,
					assets: [],
					appliedControls: [],
					vulnerabilities: [],
					properties: {}
				}
			} as Node
		];
		dirty = true;
	}

	function toggleOperator(id: string) {
		nodes = nodes.map((node) =>
			node.id === id
				? { ...node, data: { ...node.data, operator: node.data.operator === 'AND' ? 'OR' : 'AND' } }
				: node
		);
		dirty = true;
	}

	// AND cannot be a per-edge parameter, so a junction is a real node.
	// auto-inserted on the second incoming edge to keep it one click.
	async function reconcileOperator(targetId: string) {
		const target = nodes.find((node) => node.id === targetId);
		if (!target || target.type === 'operator') return;

		const incoming = edges.filter((edge) => edge.target === targetId);
		const existing = nodes.find(
			(node) =>
				node.type === 'operator' && edges.some((e) => e.source === node.id && e.target === targetId)
		);

		if (incoming.length > 1 && !existing) {
			const opId = crypto.randomUUID();
			const lane = target.parentId;
			nodes = [
				...nodes,
				{
					id: opId,
					type: 'operator',
					// lives in the target's lane so it travels with the columns
					position: { x: Math.max(0, target.position.x - 70), y: target.position.y + 30 },
					...(lane ? { parentId: lane, extent: 'parent' as const } : {}),
					draggable: true,
					deletable: true,
					connectable: true,
					// alternatives are the common case, and auto-link builds exactly that
					data: { kind: 'operator', operator: 'OR', tactic: (target.data as any).tactic }
				} as Node
			];
			edges = [
				...incoming.map((edge) => ({ ...edge, target: opId, id: `e-${edge.source}-${opId}` })),
				{
					id: `e-${opId}-${targetId}`,
					source: opId,
					target: targetId,
					markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' },
					style: 'stroke: var(--color-surface-500); stroke-width: 2;'
				},
				...edges.filter((edge) => edge.target !== targetId)
			];
		}
	}

	async function handleConnect(connection: Connection) {
		dirty = true;
		await tick();
		if (connection.target) await reconcileOperator(connection.target);
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
		const cellKey = `${technique.id}:${tacticOf(lane.id)}`;
		if (placedIds.has(cellKey)) return;
		// the backend rejects a technique in a tactic it does not belong to, so
		// refuse the drop rather than let it fail on save
		if (!laneAccepts(lane.id, technique.tactics ?? null)) return;

		const point = screenToFlowPosition({ x: event.clientX, y: event.clientY });
		nodes = [
			...nodes,
			{
				// the row's real primary key, minted here so save needs no temp-id mapping
				id: crypto.randomUUID(),
				type: 'technique',
				position: { x: point.x - lane.position.x, y: point.y - lane.position.y },
				parentId: lane.id,
				extent: 'parent',
				draggable: true,
				deletable: true,
				connectable: true,
				data: {
					kind: 'technique',
					technique: technique.id,
					tactic: tacticOf(lane.id),
					label: technique.name,
					customLabel: '',
					refId: technique.ref_id,
					parentName: technique.parentName ?? null,
					description: '',
					isHighlighted: false,
					assets: [],
					appliedControls: [],
					vulnerabilities: [],
					properties: {}
				}
			} as Node
		];
		dirty = true;
		refreshLaneCounts();
	}

	// every node in an occupied lane feeds every node in the next occupied one.
	// additive: a draft to prune, not a layout
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
		// only sizes are persisted: lane x is derived from the visible set
		const laneGeometry: Record<string, { width: number; height: number }> = {};
		for (const node of nodes) {
			if (node.type !== 'lane') continue;
			const stored = graphColumns[node.id];
			laneGeometry[node.id] = {
				// a hidden lane is not measured; keep what was stored rather than reset it
				width: node.measured?.width ?? stored?.width ?? LANE_WIDTH,
				height: node.measured?.height ?? stored?.height ?? LANE_HEIGHT
			};
		}

		return {
			nodes: nodes
				.filter((node) => node.type !== 'lane')
				.map((node) => {
					const data = node.data as any;
					return {
						id: node.id,
						kind: data.kind,
						operator: data.operator ?? null,
						technique: data.technique ?? null,
						tactic: node.parentId ? tacticOf(node.parentId) : (data.tactic ?? null),
						label: data.customLabel ?? '',
						description: data.description ?? '',
						is_highlighted: Boolean(data.isHighlighted),
						assets: data.assets ?? [],
						applied_controls: data.appliedControls ?? [],
						vulnerabilities: data.vulnerabilities ?? [],
						properties: data.properties ?? {},
						position_x: node.position.x,
						position_y: node.position.y
					};
				}),
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
			nodeTypes={{
				technique: TechniqueNodeComponent,
				operator: OperatorNodeComponent,
				lane: LaneNodeComponent
			}}
			{isValidConnection}
			onconnect={handleConnect}
			ondelete={handleDelete}
			onnodedragstop={() => (dirty = true)}
			onnodeclick={({ node }) => (selectedNodeId = node.type === 'lane' ? null : node.id)}
			onpaneclick={() => (selectedNodeId = null)}
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
						<button type="button" class="btn btn-sm preset-tonal-surface" onclick={addCustomNode}>
							<i class="fa-solid fa-plus mr-1"></i>{m.addCustomNode()}
						</button>
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

	{#if !readonly}
		<NodeInspector
			node={selectedNode}
			onUpdate={patchSelected}
			onDelete={(id) => {
				removeNode(id);
				selectedNodeId = null;
			}}
		/>
	{/if}
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
