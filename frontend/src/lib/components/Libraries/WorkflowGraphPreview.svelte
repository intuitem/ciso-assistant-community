<script lang="ts">
	import { SvelteFlow, Background, useSvelteFlow, type Node, type Edge } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { setContext, onMount } from 'svelte';
	import {
		EDGE_STYLE,
		EDGE_MARKER,
		NODE_TYPE_LABELS
	} from '../../../routes/(app)/(internal)/workflows/[id=uuid]/node-visuals';
	import StepNode from '../../../routes/(app)/(internal)/workflows/[id=uuid]/nodes/StepNode.svelte';
	import ConditionNode from '../../../routes/(app)/(internal)/workflows/[id=uuid]/nodes/ConditionNode.svelte';
	import TerminalNode from '../../../routes/(app)/(internal)/workflows/[id=uuid]/nodes/TerminalNode.svelte';
	import TriggerNode from '../../../routes/(app)/(internal)/workflows/[id=uuid]/nodes/TriggerNode.svelte';
	import LoopNode from '../../../routes/(app)/(internal)/workflows/[id=uuid]/nodes/LoopNode.svelte';
	import WorkflowEdge from '../../../routes/(app)/(internal)/workflows/[id=uuid]/edges/WorkflowEdge.svelte';
	import { computeLayout } from '../../../routes/(app)/(internal)/workflows/[id=uuid]/graph-layout';

	// The library-export graph shape (ref-keyed, branch NAMES, no positions) —
	// see backend/workflows/import_export.py. Rendered read-only; no ops proxy,
	// autosave or version state, so this is deliberately NOT WorkflowCanvas.
	interface Props {
		graph: { nodes?: any[]; edges?: any[]; variables?: any[] };
	}
	let { graph }: Props = $props();

	// Read-only editor context: node components gate their delete / add-branch
	// affordances on !readonly, so no-ops are never reached.
	setContext('workflowEditor', {
		readonly: true,
		deleteNode: () => {},
		addBranch: () => {}
	});

	const nodeTypes = {
		step: StepNode,
		condition: ConditionNode,
		terminal: TerminalNode,
		trigger: TriggerNode,
		loop: LoopNode
	};
	const edgeTypes = { workflow: WorkflowEdge };

	function nodeMeta(node: any): string | null {
		switch (node.type) {
			case 'action': {
				const c = node.action_config ?? {};
				if (['create_object', 'update_object', 'read_objects'].includes(c.type))
					return c.model ? `${c.type} · ${c.model}` : c.type;
				return c.type ?? null;
			}
			case 'subprocess':
				return node.subprocess_workflow ?? null;
			case 'event':
				return node.event_key || null;
			case 'loop':
				return (node.loop_config?.collection ?? '').replace(/^\{\{\s*|\s*\}\}$/g, '') || null;
			case 'trigger': {
				const c = node.trigger_config ?? {};
				if (c.type === 'schedule') return c.cron_expression || null;
				if (c.type === 'internal_event') return c.event_key || null;
				if (c.type === 'webhook') return 'webhook';
				return null;
			}
			default:
				return null;
		}
	}

	// Branch ports key on the branch NAME here (export edges reference branches
	// by name), matching sourceHandle below.
	function branchVisuals(node: any) {
		const branches = [...(node.branches ?? [])].sort(
			(a, b) => Number(!!a.is_default) - Number(!!b.is_default)
		);
		return branches.map((b) => ({
			branchId: b.name,
			name: b.name,
			isDefault: !!b.is_default,
			wired: true
		}));
	}

	function toFlowNode(node: any): Node {
		return {
			id: node.ref,
			type:
				node.type === 'end'
					? 'terminal'
					: ['trigger', 'condition', 'loop'].includes(node.type)
						? node.type
						: 'step',
			position: { x: 0, y: 0 },
			draggable: false,
			deletable: false,
			connectable: false,
			data: {
				nodeType: node.type,
				label: node.label || NODE_TYPE_LABELS[node.type]?.() || node.type,
				meta: nodeMeta(node),
				branches: node.type === 'condition' ? branchVisuals(node) : undefined,
				triggerType: node.type === 'trigger' ? (node.trigger_config?.type ?? 'manual') : undefined,
				registration: null,
				error: null,
				domain: node
			}
		} as Node;
	}

	function toFlowEdge(edge: any, index: number): Edge {
		return {
			id: `${edge.source}->${edge.target}-${index}`,
			type: 'workflow',
			source: edge.source,
			target: edge.target,
			sourceHandle: edge.source_branch ?? (edge.source_port || undefined),
			label: edge.label || undefined,
			deletable: false,
			markerEnd: EDGE_MARKER,
			style: EDGE_STYLE
		} as Edge;
	}

	let nodes = $state<Node[]>((graph.nodes ?? []).map(toFlowNode));
	let edges = $state<Edge[]>((graph.edges ?? []).map(toFlowEdge));
	let colorMode = $state<'dark' | 'light'>('light');

	// Export carries no positions — lay out with the same dagre pass the builder
	// uses. Re-run after mount so measured sizes refine the placement.
	function layout() {
		const positions = computeLayout(nodes, edges);
		nodes = nodes.map((n) => ({ ...n, position: positions.get(n.id) ?? n.position }));
	}
	layout();

	// Grab the flow instance in oninit (same as the builder canvas): the
	// SvelteFlow provider context exists by then. Re-layout with measured
	// sizes, then fit to the settled graph — the fitView prop only fires on
	// init, before the layout refines.
	let flow: ReturnType<typeof useSvelteFlow> | null = null;
	function onInit() {
		flow = useSvelteFlow();
		setTimeout(() => {
			layout();
			setTimeout(() => flow?.fitView({ padding: 0.15, maxZoom: 1 }), 60);
		}, 60);
	}
	onMount(() => {
		colorMode = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
	});
</script>

<div
	class="h-[60vh] w-full rounded-base border border-surface-200-800"
	data-testid="workflow-preview-graph"
>
	<SvelteFlow
		bind:nodes
		bind:edges
		{colorMode}
		{nodeTypes}
		{edgeTypes}
		nodesDraggable={false}
		nodesConnectable={false}
		elementsSelectable={false}
		fitView
		oninit={onInit}
		proOptions={{ hideAttribution: true }}
	>
		<Background />
	</SvelteFlow>
</div>
