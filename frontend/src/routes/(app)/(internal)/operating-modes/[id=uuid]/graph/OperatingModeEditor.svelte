<script lang="ts">
	import { m } from '$paraglide/messages';
	import { enhance } from '$app/forms';
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

	const STAGE_X: Record<number, number> = { 0: 0, 1: 300, 2: 600, 3: 900 };
	const NODE_GAP_Y = 100;

	const nodeTypes = {
		action: ActionNodeComponent
	};

	// ---- State ----

	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);
	let logicOps = $state<Map<string, 'AND' | 'OR'>>(new Map());
	let saving = $state(false);
	let dirty = $state(false);

	// ---- Stage helpers ----

	function getStageNumber(attackStage: string): number {
		if (attackStage.includes('Reconnaissance') || attackStage === 'ebiosReconnaissance') return 0;
		if (attackStage.includes('Initial') || attackStage === 'ebiosInitialAccess') return 1;
		if (attackStage.includes('Discovery') || attackStage === 'ebiosDiscovery') return 2;
		if (attackStage.includes('Exploitation') || attackStage === 'ebiosExploitation') return 3;
		return 0;
	}

	// ---- Initialize from existing kill chain ----

	function initFromKillChain() {
		const flowNodes: Node[] = [];
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

			flowNodes.push({
				id: eaId,
				type: 'action',
				position: { x: STAGE_X[stage], y: 80 + count * NODE_GAP_Y },
				data: {
					label: ea.name,
					iconClass: ea.icon_fa_class ?? '',
					stage,
					onDelete: handleDeleteNode,
					onToggleOperator: handleToggleOperator,
					logicOperator: hasLogicOp ? step.logic_operator : undefined
				}
			});
			stageCount[stage] = count + 1;

			for (const ant of antecedents) {
				const antId = typeof ant === 'object' ? ant.id : ant;
				flowEdges.push({
					id: `e-${antId}-${eaId}`,
					source: antId,
					target: eaId,
					markerEnd: { type: MarkerType.ArrowClosed, color: '#4D179A' },
					style: 'stroke: #8FA1B9; stroke-width: 1.5;'
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

		// Source stage must be <= target stage
		if (sourceStage > targetStage) return false;
		// KNOW stage can't receive connections
		if (targetStage === 0) return false;
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

		const operator = incomingCount >= 2 ? (logicOps.get(nodeId) ?? 'AND') : undefined;
		nodes = nodes.map((n) =>
			n.id === nodeId ? { ...n, data: { ...n.data, logicOperator: operator } } : n
		);
	}

	// ---- Event handlers ----

	function handleConnect(connection: Connection) {
		if (!isValidConnection(connection)) return;

		const newEdge: Edge = {
			id: `e-${connection.source}-${connection.target}`,
			source: connection.source!,
			target: connection.target!,
			markerEnd: { type: MarkerType.ArrowClosed, color: '#4D179A' },
			style: 'stroke: #8FA1B9; stroke-width: 1.5;'
		};
		edges = [...edges, newEdge];

		updateNodeLogicData(connection.target!);
		dirty = true;
	}

	function handleDeleteNode(nodeId: string) {
		// Collect targets of outgoing edges (they might need logic operator update)
		const affectedTargets = edges.filter((e) => e.source === nodeId).map((e) => e.target);

		nodes = nodes.filter((n) => n.id !== nodeId);
		edges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);

		const newOps = new Map(logicOps);
		newOps.delete(nodeId);
		logicOps = newOps;

		// Update affected targets' logic operators
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

		nodes = nodes.map((n) =>
			n.id === nodeId ? { ...n, data: { ...n.data, logicOperator: newOp } } : n
		);
		dirty = true;
	}

	function handleDelete({
		nodes: deletedNodes,
		edges: deletedEdges
	}: {
		nodes: Node[];
		edges: Edge[];
	}) {
		const newOps = new Map(logicOps);

		// Clean up logicOps for deleted nodes
		for (const node of deletedNodes) {
			newOps.delete(node.id);
		}

		// Collect targets affected by deleted edges
		const targetsToUpdate = new Set<string>();
		for (const edge of deletedEdges) {
			targetsToUpdate.add(edge.target);
		}

		logicOps = newOps;

		// Update affected target nodes' logic operator display
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
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		if (!event.dataTransfer) return;

		const actionJson = event.dataTransfer.getData('application/json');
		if (!actionJson) return;

		const action: ElementaryActionItem = JSON.parse(actionJson);
		if (placedNodeIds.has(action.id)) return;

		const stage = getStageNumber(action.attack_stage);

		// Auto-position: next available slot in the stage column
		const nodesInStage = nodes.filter(
			(n) => n.type === 'action' && (n.data as any).stage === stage
		);
		const x = STAGE_X[stage];
		const y = 80 + nodesInStage.length * NODE_GAP_Y;

		const newNode: Node = {
			id: action.id,
			type: 'action',
			position: { x, y },
			data: {
				label: action.name,
				iconClass: action.icon_fa_class ?? '',
				stage,
				onDelete: handleDeleteNode,
				onToggleOperator: handleToggleOperator
			}
		};

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

<div class="flex h-[80vh] bg-gray-50 rounded-lg overflow-hidden border border-gray-200">
	<!-- Sidebar -->
	<EditorSidebar {elementaryActions} {placedNodeIds} />

	<!-- Canvas area -->
	<div class="flex-1 flex flex-col overflow-hidden">
		<!-- Toolbar -->
		<div class="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-200">
			<div class="flex items-center gap-2 text-sm text-gray-500">
				<i class="fa-solid fa-info-circle"></i>
				<span>{m.graphEditorHelp()}</span>
			</div>
			<div class="flex items-center gap-2">
				{#if dirty}
					<span class="text-xs text-amber-600 flex items-center gap-1">
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
						class="btn preset-filled-primary-500 text-sm px-4 py-1.5"
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
		<div style="flex: 1; min-height: 0;">
			<SvelteFlow
				bind:nodes
				bind:edges
				{nodeTypes}
				{isValidConnection}
				onconnect={handleConnect}
				ondelete={handleDelete}
				ondragover={handleDragOver}
				ondrop={handleDrop}
				fitView
				defaultEdgeOptions={{
					markerEnd: { type: MarkerType.ArrowClosed, color: '#4D179A' },
					style: 'stroke: #8FA1B9; stroke-width: 1.5;'
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
		--xy-node-border-radius: 6px;
		--xy-edge-stroke: #8fa1b9;
	}
	:global(.svelte-flow .svelte-flow__edge-path) {
		stroke-width: 1.5;
	}
</style>
