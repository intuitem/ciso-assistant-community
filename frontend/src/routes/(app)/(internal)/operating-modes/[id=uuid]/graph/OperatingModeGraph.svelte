<script lang="ts">
	import { m } from '$paraglide/messages';
	import { enhance } from '$app/forms';
	import { setContext, tick, untrack } from 'svelte';
	import { slide } from 'svelte/transition';
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

	import ActionNodeComponent from './nodes/ActionNode.svelte';
	import StageColumnNodeComponent from './nodes/StageColumnNode.svelte';
	import LogicEdgeComponent from './edges/LogicEdge.svelte';
	import EditorSidebar from './EditorSidebar.svelte';

	interface ElementaryActionItem {
		id: string;
		name: string;
		attack_stage: string;
		icon_fa_class?: string;
	}

	interface KillChainStep {
		elementary_action: any;
		antecedents: any[];
		logic_operator?: string | null;
		position_x?: number;
		position_y?: number;
	}

	interface GraphColumns {
		[stageId: string]: { x: number; y: number; width: number; height: number };
	}

	interface Props {
		elementaryActions: ElementaryActionItem[];
		killChainSteps: KillChainStep[];
		operatingModeId: string;
		graphColumns?: GraphColumns;
		onSaved?: () => void;
		onCreateAction?: () => void;
		onEditAction?: (eaId: string) => void;
		readonly?: boolean;
	}

	let {
		elementaryActions,
		killChainSteps,
		operatingModeId,
		graphColumns = {},
		onSaved,
		onCreateAction,
		onEditAction,
		readonly = false
	}: Props = $props();

	const COLUMN_GAP = 350;
	const COLUMN_WIDTH = 280;
	const COLUMN_HEIGHT = 400;
	const NODE_GAP_Y = 90;
	const NODE_PADDING_X = 50;
	const NODE_PADDING_Y = 60;

	const STAGE_CONFIG = [
		{
			key: 'ebiosReconnaissance',
			icon: 'fa-magnifying-glass',
			twBg: 'bg-pink-50',
			twBorder: 'border-pink-400',
			twText: 'text-pink-500'
		},
		{
			key: 'ebiosInitialAccess',
			icon: 'fa-right-to-bracket',
			twBg: 'bg-violet-50',
			twBorder: 'border-violet-400',
			twText: 'text-violet-500'
		},
		{
			key: 'ebiosDiscovery',
			icon: 'fa-lightbulb',
			twBg: 'bg-orange-50',
			twBorder: 'border-orange-400',
			twText: 'text-orange-500'
		},
		{
			key: 'ebiosExploitation',
			icon: 'fa-bolt',
			twBg: 'bg-red-50',
			twBorder: 'border-red-400',
			twText: 'text-red-500'
		}
	];

	function stageColumnId(stage: number) {
		return `stage-col-${stage}`;
	}

	const nodeTypes = {
		action: ActionNodeComponent,
		stageColumn: StageColumnNodeComponent
	};

	const edgeTypes = {
		logic: LogicEdgeComponent
	};

	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let logicOps = $state<Map<string, 'AND' | 'OR'>>(new Map());
	let saving = $state(false);
	let dirty = $state(false);
	let dragOverStage = $state<number | null>(null);
	let showHelp = $state(false);

	setContext('killChainEditor', {
		get dragOverStage() {
			return dragOverStage;
		},
		get readonly() {
			return readonly;
		},
		deleteNode: (id: string) => handleDeleteNode(id),
		toggleOperator: (id: string) => handleToggleOperator(id),
		editNode: (id: string) => onEditAction?.(id),
		markDirty: () => (dirty = true)
	});

	const VIEWPORT_KEY = `mo-graph-viewport-${operatingModeId}`;
	let flowInstance: ReturnType<typeof useSvelteFlow> | null = null;

	function handleFlowInit() {
		flowInstance = useSvelteFlow();
		setTimeout(() => {
			const saved = localStorage.getItem(VIEWPORT_KEY);
			if (saved && !readonly) {
				flowInstance?.setViewport(JSON.parse(saved));
			} else {
				flowInstance?.fitView({ duration: 200, padding: 0.15 });
			}
		}, 100);
	}

	function saveViewport() {
		if (!flowInstance) return;
		const vp = flowInstance.getViewport();
		localStorage.setItem(VIEWPORT_KEY, JSON.stringify(vp));
	}

	function getStageNumber(attackStage: string | number): number {
		if (typeof attackStage === 'number') return attackStage;
		if (attackStage.includes('Reconnaissance') || attackStage === 'ebiosReconnaissance') return 0;
		if (attackStage.includes('Initial') || attackStage === 'ebiosInitialAccess') return 1;
		if (attackStage.includes('Discovery') || attackStage === 'ebiosDiscovery') return 2;
		if (attackStage.includes('Exploitation') || attackStage === 'ebiosExploitation') return 3;
		return 0;
	}

	function buildStageColumnNodes(): Node[] {
		return STAGE_CONFIG.map((config, stage) => {
			const colId = stageColumnId(stage);
			const saved = graphColumns[colId];
			return {
				id: colId,
				type: 'stageColumn',
				position: saved ? { x: saved.x, y: saved.y } : { x: stage * COLUMN_GAP, y: 0 },
				style: `width: ${saved?.width ?? COLUMN_WIDTH}px; height: ${saved?.height ?? COLUMN_HEIGHT}px;`,
				data: { ...config, stage },
				selectable: true,
				draggable: false,
				deletable: false,
				connectable: false
			};
		});
	}

	function initFromKillChain() {
		const flowNodes: Node[] = buildStageColumnNodes();
		const flowEdges: Edge[] = [];
		const ops = new Map<string, 'AND' | 'OR'>();
		const stageCount: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 };

		for (const step of killChainSteps) {
			const eaId =
				typeof step.elementary_action === 'object'
					? step.elementary_action.id
					: step.elementary_action;
			const ea = elementaryActions.find((a) => a.id === eaId);
			if (!ea) continue;

			const stage = getStageNumber(ea.attack_stage);
			const count = stageCount[stage] ?? 0;
			const antecedents = step.antecedents ?? [];

			const hasLogicOp = !!step.logic_operator && antecedents.length > 1;
			if (hasLogicOp) {
				ops.set(eaId, step.logic_operator as 'AND' | 'OR');
			}

			const hasSavedPosition = (step.position_x ?? 0) !== 0 || (step.position_y ?? 0) !== 0;
			const posX = hasSavedPosition ? step.position_x! : NODE_PADDING_X;
			const posY = hasSavedPosition ? step.position_y! : NODE_PADDING_Y + count * NODE_GAP_Y;

			flowNodes.push({
				id: eaId,
				type: 'action',
				position: { x: posX, y: posY },
				parentId: stageColumnId(stage),
				extent: 'parent',
				draggable: !readonly,
				deletable: !readonly,
				connectable: !readonly,
				data: {
					label: ea.name,
					iconClass: ea.icon_fa_class ?? '',
					stage,
					logicOp: hasLogicOp ? (step.logic_operator as 'AND' | 'OR') : null
				}
			} as Node);
			stageCount[stage] = count + 1;

			for (let ai = 0; ai < antecedents.length; ai++) {
				const ant = antecedents[ai];
				const antId = typeof ant === 'object' ? ant.id : ant;
				flowEdges.push({
					id: `e-${antId}-${eaId}`,
					source: antId,
					target: eaId,
					type: 'logic',
					markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' },
					style: 'stroke: var(--color-surface-500); stroke-width: 2;',
					data: {
						logicOp: ai === 0 && hasLogicOp ? step.logic_operator : null,
						targetStage: stage,
						targetNodeId: eaId
					}
				});
			}
		}

		nodes = flowNodes;
		edges = flowEdges;
		logicOps = ops;
	}

	function resetGraph() {
		initFromKillChain();
		dirty = false;
	}

	initFromKillChain();

	// Sync action node display data when elementaryActions change (e.g., after modal edit)
	$effect(() => {
		const eaMap = new Map(elementaryActions.map((ea) => [ea.id, ea]));

		untrack(() => {
			nodes = nodes.map((n) => {
				if (n.type !== 'action') return n;
				const ea = eaMap.get(n.id);
				if (!ea) return n;
				const newStage = getStageNumber(ea.attack_stage);
				return {
					...n,
					parentId: stageColumnId(newStage),
					data: {
						...n.data,
						label: ea.name,
						iconClass: ea.icon_fa_class ?? '',
						stage: newStage
					}
				};
			});
		});
	});

	let prevReadonly = readonly;
	$effect(() => {
		if (readonly !== prevReadonly) {
			prevReadonly = readonly;
			nodes = nodes.map((n) =>
				n.type === 'action'
					? { ...n, draggable: !readonly, deletable: !readonly, connectable: !readonly }
					: n
			);
		}
	});

	$effect(() => {
		void readonly;
		const timer = setTimeout(() => {
			flowInstance?.fitView({ duration: 300, padding: 0.15 });
		}, 350);
		return () => clearTimeout(timer);
	});

	$effect(() => {
		const handleBeforePrint = () => {
			flowInstance?.fitView({ padding: 0.25 });
		};
		window.addEventListener('beforeprint', handleBeforePrint);
		return () => window.removeEventListener('beforeprint', handleBeforePrint);
	});

	const placedNodeIds = $derived(
		new Set(nodes.filter((n) => n.type === 'action').map((n) => n.id))
	);

	function isValidConnection(connection: Connection): boolean {
		const sourceNode = nodes.find((n) => n.id === connection.source);
		const targetNode = nodes.find((n) => n.id === connection.target);
		if (!sourceNode || !targetNode) return false;

		const sourceStage = sourceNode.data.stage as number;
		const targetStage = targetNode.data.stage as number;

		if (sourceStage > targetStage) return false;
		if (connection.source === connection.target) return false;
		if (edges.some((e) => e.source === connection.source && e.target === connection.target))
			return false;

		return true;
	}

	function updateNodeLogicData(nodeId: string) {
		const incomingEdges = edges.filter((e) => e.target === nodeId);
		const incomingCount = incomingEdges.length;
		const newOps = new Map(logicOps);

		if (incomingCount >= 2 && !newOps.has(nodeId)) {
			newOps.set(nodeId, 'AND');
		} else if (incomingCount < 2) {
			newOps.delete(nodeId);
		}
		logicOps = newOps;

		const op = newOps.get(nodeId) ?? null;
		const targetNode = nodes.find((n) => n.id === nodeId);
		const targetStage = (targetNode?.data as any)?.stage ?? 0;
		const firstIncomingId = incomingEdges[0]?.id;

		nodes = nodes.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, logicOp: op } } : n));
		edges = edges.map((e) =>
			e.target === nodeId
				? {
						...e,
						data: {
							...e.data,
							logicOp: e.id === firstIncomingId ? op : null,
							targetStage,
							targetNodeId: nodeId
						}
					}
				: e
		);
	}

	async function handleConnect(connection: Connection) {
		dirty = true;

		const targetNode = nodes.find((n) => n.id === connection.target);
		const targetStage = (targetNode?.data as any)?.stage ?? 0;
		edges = edges.map((e) =>
			e.source === connection.source && e.target === connection.target
				? {
						...e,
						type: 'logic',
						data: { logicOp: null, targetStage, targetNodeId: connection.target }
					}
				: e
		);

		await tick();
		updateNodeLogicData(connection.target);
	}

	async function handleDeleteNode(nodeId: string) {
		const affectedTargets = edges.filter((e) => e.source === nodeId).map((e) => e.target);

		nodes = nodes.filter((n) => n.id !== nodeId);
		edges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);

		const newOps = new Map(logicOps);
		newOps.delete(nodeId);
		logicOps = newOps;
		dirty = true;

		await tick();
		for (const targetId of affectedTargets) {
			if (nodes.some((n) => n.id === targetId)) {
				updateNodeLogicData(targetId);
			}
		}
	}

	function handleToggleOperator(nodeId: string) {
		const current = logicOps.get(nodeId) ?? 'AND';
		const newOp = current === 'AND' ? 'OR' : 'AND';
		logicOps = new Map(logicOps).set(nodeId, newOp);

		const incomingEdges = edges.filter((e) => e.target === nodeId);
		const firstIncomingId = incomingEdges[0]?.id;

		nodes = nodes.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, logicOp: newOp } } : n));
		edges = edges.map((e) =>
			e.target === nodeId
				? { ...e, data: { ...e.data, logicOp: e.id === firstIncomingId ? newOp : null } }
				: e
		);
		dirty = true;
	}

	async function handleDeleteEdge(edgeId: string) {
		const edge = edges.find((e) => e.id === edgeId);
		if (!edge) return;
		edges = edges.filter((e) => e.id !== edgeId);
		dirty = true;

		await tick();
		updateNodeLogicData(edge.target);
	}

	function handleEdgeClick(edge: Edge, event: MouseEvent) {
		handleDeleteEdge(edge.edge.id);
	}

	async function handleDelete({
		nodes: deletedNodes,
		edges: deletedEdges
	}: {
		nodes: Node[];
		edges: Edge[];
	}) {
		const newOps = new Map(logicOps);

		for (const node of deletedNodes) {
			newOps.delete(node.id);
		}

		const targetsToUpdate = new Set<string>();
		for (const edge of deletedEdges) {
			targetsToUpdate.add(edge.target);
		}

		logicOps = newOps;

		await tick();
		for (const targetId of targetsToUpdate) {
			if (nodes.some((n) => n.id === targetId)) {
				updateNodeLogicData(targetId);
			}
		}

		dirty = true;
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
		const json = event.dataTransfer?.types.includes('application/json');
		if (json) {
			dragOverStage = -1;
		}
	}

	function handleDragLeave() {
		dragOverStage = null;
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragOverStage = null;
		if (!event.dataTransfer) return;

		const actionJson = event.dataTransfer.getData('application/json');
		if (!actionJson) return;

		const action: ElementaryActionItem = JSON.parse(actionJson);
		if (placedNodeIds.has(action.id)) return;

		const stage = getStageNumber(action.attack_stage);

		const nodesInStage = nodes.filter(
			(n) => n.type === 'action' && (n.data as any).stage === stage
		);

		const newNode: Node = {
			id: action.id,
			type: 'action',
			position: { x: NODE_PADDING_X, y: NODE_PADDING_Y + nodesInStage.length * NODE_GAP_Y },
			parentId: stageColumnId(stage),
			extent: 'parent',
			draggable: true,
			deletable: true,
			connectable: true,
			data: {
				label: action.name,
				iconClass: action.icon_fa_class ?? '',
				stage,
				logicOp: null
			}
		} as Node;

		nodes = [...nodes, newNode];
		dirty = true;
	}

	function buildKillChainStepsJson(): string {
		const actionNodes = nodes.filter((n) => n.type === 'action');

		const steps = actionNodes.map((node) => {
			const antecedentIds = edges.filter((e) => e.target === node.id).map((e) => e.source);

			return {
				elementary_action: node.id,
				antecedents: antecedentIds,
				logic_operator:
					antecedentIds.length > 1
						? ((node.data as any).logicOp ?? logicOps.get(node.id) ?? 'AND')
						: null,
				is_highlighted: false,
				position_x: node.position.x,
				position_y: node.position.y
			};
		});

		return JSON.stringify(steps);
	}

	function buildGraphColumnsJson(): string {
		const columns: GraphColumns = {};
		for (const node of nodes) {
			if (node.type === 'stageColumn') {
				const w = node.measured?.width ?? node.width ?? COLUMN_WIDTH;
				const h = node.measured?.height ?? node.height ?? COLUMN_HEIGHT;
				columns[node.id] = {
					x: node.position.x,
					y: node.position.y,
					width: w,
					height: h
				};
			}
		}
		return JSON.stringify(columns);
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="flex h-full bg-surface-50 rounded-base overflow-hidden border border-surface-200">
	{#if !readonly}
		<div transition:slide={{ axis: 'x', duration: 300 }}>
			<EditorSidebar {elementaryActions} {placedNodeIds} {onCreateAction} />
		</div>
	{/if}

	<div class="flex-1 flex flex-col overflow-hidden">
		<div class="flex-1 min-h-0">
			<SvelteFlow
				bind:nodes
				bind:edges
				{nodeTypes}
				{edgeTypes}
				isValidConnection={readonly ? () => false : isValidConnection}
				onconnect={readonly ? undefined : handleConnect}
				onnodedragstop={readonly ? undefined : () => (dirty = true)}
				ondelete={readonly ? undefined : handleDelete}
				onedgeclick={readonly ? undefined : handleEdgeClick}
				ondragover={readonly ? undefined : handleDragOver}
				ondragleave={readonly ? undefined : handleDragLeave}
				ondrop={readonly ? undefined : handleDrop}
				nodesDraggable={!readonly}
				nodesConnectable={!readonly}
				elementsSelectable={!readonly}
				oninit={handleFlowInit}
				onmoveend={saveViewport}
				snapGrid={[10, 10]}
				minZoom={0.3}
				proOptions={{ hideAttribution: true }}
				defaultEdgeOptions={{
					type: 'logic',
					markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' },
					style: 'stroke: var(--color-surface-500); stroke-width: 2;'
				}}
			>
				<Background variant={BackgroundVariant.Dots} gap={20} />
				{#if !readonly}
					<Panel position="top-left">
						<div class="flex items-start gap-2">
							<button
								type="button"
								aria-label="Toggle help"
								class="nopan nodrag w-6 h-6 rounded-full preset-tonal flex items-center justify-center cursor-pointer hover:brightness-90 transition-colors"
								onclick={() => (showHelp = !showHelp)}
							>
								<i class="fa-solid fa-info text-xs"></i>
							</button>
							{#if showHelp}
								<p
									class="text-xs bg-surface-100 text-surface-700 border border-surface-300 rounded-base px-3 py-2 max-w-xs leading-relaxed"
									transition:slide={{ axis: 'x', duration: 200 }}
								>
									{m.graphEditorHelp()}
								</p>
							{/if}
						</div>
					</Panel>
					{#if dirty}
						<Panel position="top-right">
							<div class="flex items-center gap-2">
								<span class="text-xs text-warning-500 flex items-center gap-1">
									<i class="fa-solid fa-circle text-[6px]"></i>
									{m.unsavedChanges()}
								</span>
								<button type="button" class="btn preset-tonal text-sm" onclick={resetGraph}>
									<i class="fa-solid fa-rotate-left mr-1"></i>
									{m.discardChanges()}
								</button>
								<form
									method="POST"
									action="?/saveGraph"
									use:enhance={() => {
										saving = true;
										return async ({ result, update }) => {
											saving = false;
											if (result.type === 'success') {
												dirty = false;
												saveViewport();
												onSaved?.();
											}
											await update();
										};
									}}
								>
									<input type="hidden" name="kill_chain_steps" value={buildKillChainStepsJson()} />
									<input type="hidden" name="graph_columns" value={buildGraphColumnsJson()} />
									<button
										type="submit"
										class="btn preset-filled-primary-500 text-sm"
										disabled={saving}
									>
										{#if saving}
											<i class="fa-solid fa-spinner fa-spin mr-1"></i>
										{:else}
											<i class="fa-solid fa-save mr-1"></i>
										{/if}
										{m.save()}
									</button>
								</form>
							</div>
						</Panel>
					{/if}
					<Controls showLock={false} />
					<MiniMap />
				{/if}
			</SvelteFlow>
		</div>
	</div>
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
	:global(.svelte-flow .svelte-flow__edge:hover .svelte-flow__edge-path) {
		stroke: var(--color-error-500);
		cursor: pointer;
	}
</style>
