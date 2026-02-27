<script lang="ts">
	import { m } from '$paraglide/messages';
	import { enhance } from '$app/forms';
	import { setContext } from 'svelte';
	import {
		SvelteFlow,
		Controls,
		Background,
		BackgroundVariant,
		MiniMap,
		type Node,
		type Edge,
		type Connection,
		MarkerType
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import ActionNodeComponent from './nodes/ActionNode.svelte';
	import StageColumnNodeComponent from './nodes/StageColumnNode.svelte';
	import EditorSidebar from './EditorSidebar.svelte';

	// ---- Types ----

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
	}

	// ---- Props ----

	interface Props {
		elementaryActions: ElementaryActionItem[];
		killChainSteps: KillChainStep[];
		operatingModeId: string;
		onSaved?: () => void;
	}

	let { elementaryActions, killChainSteps, operatingModeId, onSaved }: Props = $props();

	// ---- Constants ----

	const COLUMN_GAP = 350;
	const COLUMN_WIDTH = 280;
	const COLUMN_HEIGHT = 800;
	const NODE_GAP_Y = 90;
	const NODE_PADDING_X = 50;
	const NODE_PADDING_Y = 60;

	const STAGE_CONFIG = [
		{ key: 'ebiosReconnaissance', icon: 'fa-magnifying-glass', twBg: 'bg-pink-50', twBorder: 'border-pink-400', twText: 'text-pink-500' },
		{ key: 'ebiosInitialAccess', icon: 'fa-right-to-bracket', twBg: 'bg-violet-50', twBorder: 'border-violet-400', twText: 'text-violet-500' },
		{ key: 'ebiosDiscovery', icon: 'fa-lightbulb', twBg: 'bg-orange-50', twBorder: 'border-orange-400', twText: 'text-orange-500' },
		{ key: 'ebiosExploitation', icon: 'fa-bolt', twBg: 'bg-red-50', twBorder: 'border-red-400', twText: 'text-red-500' }
	];

	function stageColumnId(stage: number) {
		return `stage-col-${stage}`;
	}

	const nodeTypes = {
		action: ActionNodeComponent,
		stageColumn: StageColumnNodeComponent
	};

	// ---- State ----

	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let logicOps = $state<Map<string, 'AND' | 'OR'>>(new Map());
	let saving = $state(false);
	let dirty = $state(false);
	let dragOverStage = $state<number | null>(null);

	// ---- Context for child components (ActionNode, StageColumnNode) ----

	setContext('killChainEditor', {
		get logicOps() {
			return logicOps;
		},
		get dragOverStage() {
			return dragOverStage;
		},
		deleteNode: (id: string) => handleDeleteNode(id),
		toggleOperator: (id: string) => handleToggleOperator(id)
	});

	// ---- Stage helpers ----

	function getStageNumber(attackStage: string): number {
		if (attackStage.includes('Reconnaissance') || attackStage === 'ebiosReconnaissance') return 0;
		if (attackStage.includes('Initial') || attackStage === 'ebiosInitialAccess') return 1;
		if (attackStage.includes('Discovery') || attackStage === 'ebiosDiscovery') return 2;
		if (attackStage.includes('Exploitation') || attackStage === 'ebiosExploitation') return 3;
		return 0;
	}

	// ---- Build stage column parent nodes ----

	function buildStageColumnNodes(): Node[] {
		return STAGE_CONFIG.map((config, stage) => ({
			id: stageColumnId(stage),
			type: 'stageColumn',
			position: { x: stage * COLUMN_GAP, y: 0 },
			style: `width: ${COLUMN_WIDTH}px; height: ${COLUMN_HEIGHT}px;`,
			data: { ...config, stage },
			selectable: true,
			draggable: false,
			deletable: false,
			connectable: false
		}));
	}

	// ---- Initialize from existing kill chain ----

	function initFromKillChain() {
		// Parent column nodes must come first in the array
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

			// Position is relative to the parent column node
			flowNodes.push({
				id: eaId,
				type: 'action',
				position: { x: NODE_PADDING_X, y: NODE_PADDING_Y + count * NODE_GAP_Y },
				parentId: stageColumnId(stage),
				extent: 'parent',
				data: {
					label: ea.name,
					iconClass: ea.icon_fa_class ?? '',
					stage
				}
			} as Node);
			stageCount[stage] = count + 1;

			for (const ant of antecedents) {
				const antId = typeof ant === 'object' ? ant.id : ant;
				flowEdges.push({
					id: `e-${antId}-${eaId}`,
					source: antId,
					target: eaId,
					markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-primary-800)' },
					style: 'stroke: var(--color-surface-400); stroke-width: 1.5;'
				});
			}
		}

		nodes = flowNodes;
		edges = flowEdges;
		logicOps = ops;
	}

	$effect(() => {
		initFromKillChain();
	});

	// ---- Derived ----

	const placedNodeIds = $derived(new Set(nodes.filter((n) => n.type === 'action').map((n) => n.id)));

	// ---- Connection validation ----

	function isValidConnection(connection: Connection): boolean {
		const sourceNode = nodes.find((n) => n.id === connection.source);
		const targetNode = nodes.find((n) => n.id === connection.target);
		if (!sourceNode || !targetNode) return false;

		const sourceStage = sourceNode.data.stage as number;
		const targetStage = targetNode.data.stage as number;

		// Source stage must be <= target stage (same stage allowed)
		if (sourceStage > targetStage) return false;
		// No self-connections
		if (connection.source === connection.target) return false;
		// No duplicates
		if (edges.some((e) => e.source === connection.source && e.target === connection.target))
			return false;

		return true;
	}

	// ---- Node logic operator helpers ----

	function updateNodeLogicData(nodeId: string) {
		const incomingCount = edges.filter((e) => e.target === nodeId).length;
		const newOps = new Map(logicOps);

		if (incomingCount >= 2 && !newOps.has(nodeId)) {
			newOps.set(nodeId, 'AND');
		} else if (incomingCount < 2) {
			newOps.delete(nodeId);
		}
		logicOps = newOps;
	}

	// ---- Event handlers ----

	function handleConnect(connection: Connection) {
		if (!isValidConnection(connection)) return;

		const newEdge: Edge = {
			id: `e-${connection.source}-${connection.target}`,
			source: connection.source!,
			target: connection.target!,
			markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-primary-800)' },
			style: 'stroke: var(--color-surface-400); stroke-width: 1.5;'
		};
		edges = [...edges, newEdge];

		updateNodeLogicData(connection.target!);
		dirty = true;
	}

	function handleDeleteNode(nodeId: string) {
		const affectedTargets = edges.filter((e) => e.source === nodeId).map((e) => e.target);

		nodes = nodes.filter((n) => n.id !== nodeId);
		edges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);

		const newOps = new Map(logicOps);
		newOps.delete(nodeId);
		logicOps = newOps;

		for (const targetId of affectedTargets) {
			if (nodes.some((n) => n.id === targetId)) {
				updateNodeLogicData(targetId);
			}
		}

		dirty = true;
	}

	function handleToggleOperator(nodeId: string) {
		const current = logicOps.get(nodeId) ?? 'AND';
		const newOp = current === 'AND' ? 'OR' : 'AND';
		logicOps = new Map(logicOps).set(nodeId, newOp);
		dirty = true;
	}

	function handleDeleteEdge(edgeId: string) {
		const edge = edges.find((e) => e.id === edgeId);
		if (!edge) return;
		edges = edges.filter((e) => e.id !== edgeId);
		updateNodeLogicData(edge.target);
		dirty = true;
	}

	function handleEdgeClick(_event: MouseEvent, edge: Edge) {
		handleDeleteEdge(edge.id);
	}

	function handleDelete({
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

		for (const targetId of targetsToUpdate) {
			if (nodes.some((n) => n.id === targetId)) {
				updateNodeLogicData(targetId);
			}
		}

		dirty = true;
	}

	// ---- Drag & Drop from sidebar ----

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

		// Count existing nodes in this stage column
		const nodesInStage = nodes.filter(
			(n) => n.type === 'action' && (n.data as any).stage === stage
		);

		// Position relative to the parent column node
		const newNode: Node = {
			id: action.id,
			type: 'action',
			position: { x: NODE_PADDING_X, y: NODE_PADDING_Y + nodesInStage.length * NODE_GAP_Y },
			parentId: stageColumnId(stage),
			extent: 'parent',
			data: {
				label: action.name,
				iconClass: action.icon_fa_class ?? '',
				stage
			}
		} as Node;

		nodes = [...nodes, newNode];
		dirty = true;
	}

	// ---- Save ----

	function buildKillChainStepsJson(): string {
		const actionNodes = nodes.filter((n) => n.type === 'action');

		const steps = actionNodes.map((node) => {
			const antecedentIds = edges.filter((e) => e.target === node.id).map((e) => e.source);

			return {
				elementary_action: node.id,
				antecedents: antecedentIds,
				logic_operator: antecedentIds.length > 1 ? (logicOps.get(node.id) ?? 'AND') : null,
				is_highlighted: false
			};
		});

		return JSON.stringify(steps);
	}
</script>

<div class="flex h-[80vh] bg-surface-50 rounded-base overflow-hidden border border-surface-200">
	<!-- Sidebar -->
	<EditorSidebar {elementaryActions} {placedNodeIds} />

	<!-- Canvas area -->
	<div class="flex-1 flex flex-col overflow-hidden">
		<!-- Toolbar -->
		<div
			class="flex items-center justify-between px-4 py-2 bg-white border-b border-surface-200"
		>
			<div class="flex items-center gap-2 text-sm text-surface-500">
				<i class="fa-solid fa-info-circle"></i>
				<span>{m.graphEditorHelp()}</span>
			</div>
			<div class="flex items-center gap-2">
				{#if dirty}
					<span class="text-xs text-warning-500 flex items-center gap-1">
						<i class="fa-solid fa-circle text-[6px]"></i>
						{m.unsavedChanges()}
					</span>
				{/if}
				<form
					method="POST"
					action="?/saveGraph"
					use:enhance={() => {
						saving = true;
						return async ({ update }) => {
							saving = false;
							dirty = false;
							onSaved?.();
							await update();
						};
					}}
				>
					<input type="hidden" name="kill_chain_steps" value={buildKillChainStepsJson()} />
					<button
						type="submit"
						class="btn preset-filled-primary-500 text-sm"
						disabled={saving || !dirty}
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
		</div>

		<!-- Svelte Flow Canvas -->
		<div class="flex-1 min-h-0">
			<SvelteFlow
				bind:nodes
				bind:edges
				{nodeTypes}
				{isValidConnection}
				onconnect={handleConnect}
				ondelete={handleDelete}
				onedgeclick={handleEdgeClick}
				ondragover={handleDragOver}
				ondragleave={handleDragLeave}
				ondrop={handleDrop}
				snapGrid={[10, 10]}
				fitView
				defaultEdgeOptions={{
					markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-primary-800)' },
					style: 'stroke: var(--color-surface-400); stroke-width: 1.5;'
				}}
			>
				<Background variant={BackgroundVariant.Dots} gap={20} />
				<Controls />
				<MiniMap />
			</SvelteFlow>
		</div>
	</div>
</div>

<style>
	:global(.svelte-flow) {
		--xy-node-border-radius: var(--radius-base);
		--xy-edge-stroke: var(--color-surface-400);
	}
	:global(.svelte-flow .svelte-flow__edge-path) {
		stroke-width: 1.5;
	}
	:global(.svelte-flow .svelte-flow__edge:hover .svelte-flow__edge-path) {
		stroke: var(--color-error-500);
		cursor: pointer;
	}
</style>
