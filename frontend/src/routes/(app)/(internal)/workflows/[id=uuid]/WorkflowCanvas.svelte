<script lang="ts">
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { setContext } from 'svelte';
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

	import Palette from './Palette.svelte';
	import Inspector from './Inspector.svelte';
	import RunsPanel from './RunsPanel.svelte';
	import StepNode from './nodes/StepNode.svelte';
	import TerminalNode from './nodes/TerminalNode.svelte';

	interface Props {
		graph: any;
		workflowId: string;
		versionId: string;
		folderId: string;
		readonly: boolean;
		roles: any[];
		actors: any[];
		taskTemplates: any[];
		subprocessCandidates: any[];
		creatableModels?: any[];
		fkOptions?: Record<string, any[]>;
		hookUrl?: string | null;
	}

	let {
		graph,
		workflowId,
		versionId,
		folderId,
		readonly,
		roles,
		actors,
		taskTemplates,
		subprocessCandidates,
		creatableModels = [],
		fkOptions = {},
		hookUrl = null
	}: Props = $props();

	function opsUrl(action: string) {
		return `/workflows/${workflowId}/ops?action=${action}`;
	}

	const nodeTypes = { step: StepNode, terminal: TerminalNode };

	const EDGE_STYLE = 'stroke: var(--color-surface-500); stroke-width: 2;';
	const EDGE_MARKER = { type: MarkerType.ArrowClosed, color: 'var(--color-surface-600)' };

	// ---------- domain → canvas ----------

	function nodeMeta(domain: any): string | null {
		switch (domain.type) {
			case 'task':
				return (
					domain.task_template_name ??
					taskTemplates.find((t) => t.id === domain.task_template)?.name ??
					null
				);
			case 'action': {
				const config = domain.action_config ?? {};
				switch (config.type) {
					case 'create_object':
						return config.model ? `${config.type} · ${config.model}` : config.type;
					case 'http_request': {
						const url = (config.url ?? '').replace(/^https?:\/\//, '');
						const short = url.length > 30 ? `${url.slice(0, 30)}…` : url;
						return short ? `${config.method ?? 'GET'} ${short}` : config.type;
					}
					case 'provision_folder':
						return config.name || config.type;
					case 'provision_user':
						return config.email || config.type;
					case 'manage_group_membership':
						return `${config.operation ?? 'add'} ${config.builtin_group ?? ''}`.trim();
					default:
						return config.type ?? null;
				}
			}
			case 'subprocess':
				return (
					domain.subprocess_workflow_name ??
					subprocessCandidates.find((w) => w.id === domain.subprocess_workflow)?.name ??
					null
				);
			case 'event':
				return domain.event_key || null;
			default:
				return null;
		}
	}

	const NODE_TYPE_LABELS: Record<string, () => string> = {
		start: m.workflowNodeStart,
		end: m.workflowNodeEnd,
		task: m.workflowNodeTask,
		condition: m.workflowNodeCondition,
		action: m.workflowNodeAction,
		subprocess: m.workflowNodeSubprocess,
		event: m.workflowNodeEvent
	};

	function visualData(domain: any, error: string | null = null) {
		return {
			nodeType: domain.type,
			label: domain.label || NODE_TYPE_LABELS[domain.type]?.() || domain.type,
			meta: nodeMeta(domain),
			forkType: domain.fork_type,
			joinType: domain.join_type,
			assignments: domain.assignments ?? [],
			error,
			domain
		};
	}

	function edgeLabel(domain: any): string {
		if (domain.label) return domain.label;
		const conditions = domain.condition_groups?.[0]?.conditions ?? [];
		if (!conditions.length) return '';
		if (conditions.length === 1) {
			const condition = conditions[0];
			const key = variables.find((v) => v.id === condition.variable)?.key ?? '?';
			return condition.op === 'is_null'
				? `${key} is null`
				: `${key} ${condition.op} ${condition.value}`;
		}
		return `${conditions.length} ${m.edgeConditions().toLowerCase()}`;
	}

	function capitalize(s: string) {
		return s.charAt(0).toUpperCase() + s.slice(1);
	}

	function toFlowNode(domain: any, index: number): Node {
		const position =
			domain.position?.x !== undefined
				? { x: domain.position.x, y: domain.position.y }
				: { x: 120 + index * 220, y: 220 };
		return {
			id: domain.id,
			type: domain.type === 'start' || domain.type === 'end' ? 'terminal' : 'step',
			position,
			draggable: !readonly,
			deletable: !readonly && domain.type !== 'start',
			connectable: !readonly,
			data: visualData(domain)
		} as Node;
	}

	function toFlowEdge(domain: any): Edge {
		return {
			id: domain.id,
			source: domain.source,
			target: domain.target,
			label: edgeLabel(domain) || undefined,
			deletable: !readonly,
			markerEnd: EDGE_MARKER,
			style: EDGE_STYLE,
			data: { domain }
		} as Edge;
	}

	let variables = $state<any[]>(graph.variables ?? []);
	let nodes = $state<Node[]>((graph.nodes ?? []).map(toFlowNode));
	let edges = $state<Edge[]>((graph.edges ?? []).map(toFlowEdge));

	// A brand-new draft gets a start and an end waiting to be wired, instead of
	// an empty void.
	if (!readonly && nodes.length === 0) {
		nodes = [
			toFlowNode(newNodeDomain('start', { x: 120, y: 202 }), 0),
			toFlowNode(newNodeDomain('end', { x: 560, y: 202 }), 1)
		];
	}

	// ---------- selection ----------

	let selectedNodeId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	const selectedNode = $derived(nodes.find((n) => n.id === selectedNodeId) ?? null);
	const selectedEdge = $derived(edges.find((e) => e.id === selectedEdgeId) ?? null);

	// ---------- save machinery ----------

	let saveState = $state<'idle' | 'dirty' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state<string | null>(null);
	let saveTimer: ReturnType<typeof setTimeout> | null = null;
	let validationErrors = $state<any[]>([]);
	let publishing = $state(false);

	function markDirty() {
		if (readonly) return;
		saveState = 'dirty';
		validationErrors = [];
		if (saveTimer) clearTimeout(saveTimer);
		saveTimer = setTimeout(save, 1200);
	}

	function refreshVisuals() {
		nodes = nodes.map((n) => ({ ...n, data: visualData(n.data.domain, n.data.error ?? null) }));
		edges = edges.map((e) => ({ ...e, label: edgeLabel(e.data!.domain) || undefined }));
	}

	function serializeGraph() {
		return {
			nodes: nodes.map((n) => ({
				...(n.data.domain as object),
				position: { x: Math.round(n.position.x), y: Math.round(n.position.y) }
			})),
			edges: edges.map((e) => ({
				...(e.data!.domain as object),
				source: e.source,
				target: e.target
			})),
			variables
		};
	}

	async function save(): Promise<boolean> {
		if (readonly) return true;
		if (saveTimer) clearTimeout(saveTimer);
		saveState = 'saving';
		const res = await fetch(opsUrl('save-graph'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ version: versionId, graph: serializeGraph() })
		});
		if (!res.ok) {
			const body = await res.json().catch(() => ({}));
			saveError = body.error ?? body.detail ?? res.statusText;
			saveState = 'error';
			return false;
		}
		saveError = null;
		saveState = saveState === 'saving' ? 'saved' : saveState;
		return true;
	}

	async function publish() {
		publishing = true;
		validationErrors = [];
		try {
			if (!(await save())) return;
			const res = await fetch(opsUrl('publish'), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ version: versionId })
			});
			if (res.ok) {
				await invalidateAll();
				return;
			}
			const body = await res.json().catch(() => ({}));
			validationErrors = body.errors ?? [];
			nodes = nodes.map((n) => {
				const nodeError = validationErrors.find((e) => e.node_id === n.id);
				return { ...n, data: { ...n.data, error: nodeError?.message ?? null } };
			});
		} finally {
			publishing = false;
		}
	}

	async function newDraft() {
		const res = await fetch(opsUrl('new-draft'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ version: versionId })
		});
		if (res.ok) await invalidateAll();
	}

	let runsOpen = $state(false);
	let runsPanel = $state<RunsPanel | null>(null);
	let running = $state(false);

	async function runWorkflow() {
		running = true;
		try {
			if (!readonly && !(await save())) return;
			const res = await fetch(opsUrl('run'), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ version: versionId })
			});
			if (res.ok) {
				runsOpen = true;
				await runsPanel?.refresh();
			}
		} finally {
			running = false;
		}
	}

	// ---------- graph edits ----------

	function newNodeDomain(type: string, position?: { x: number; y: number }) {
		return {
			id: crypto.randomUUID(),
			type,
			label: '',
			fork_type: 'exclusive',
			join_type: 'none',
			task_template: null,
			subprocess_workflow: null,
			action_config: type === 'action' ? { type: 'log' } : {},
			input_mapping: {},
			output_mapping: {},
			event_key: '',
			event_filters: {},
			position: position ?? {},
			assignments: [],
			presentation: null
		};
	}

	let flowInstance: ReturnType<typeof useSvelteFlow> | null = null;

	function handleFlowInit() {
		flowInstance = useSvelteFlow();
		setTimeout(() => flowInstance?.fitView({ duration: 200, padding: 0.2, maxZoom: 1 }), 100);
	}

	function addNode(type: string, position?: { x: number; y: number }) {
		if (type === 'start' && nodes.some((n) => n.data.nodeType === 'start')) return;
		const fallback = { x: 200 + Math.random() * 80, y: 160 + Math.random() * 80 };
		const domain = newNodeDomain(type, position ?? fallback);
		const flowNode = toFlowNode(domain, 0);
		flowNode.position = position ?? fallback;
		nodes = [...nodes, flowNode];
		selectedNodeId = flowNode.id;
		selectedEdgeId = null;
		markDirty();
	}

	function handleDragOver(event: DragEvent) {
		if (event.dataTransfer?.types.includes('application/ciso-workflow-node')) {
			event.preventDefault();
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleDrop(event: DragEvent) {
		const type = event.dataTransfer?.getData('application/ciso-workflow-node');
		if (!type) return;
		event.preventDefault();
		const position = flowInstance?.screenToFlowPosition({
			x: event.clientX,
			y: event.clientY
		});
		addNode(type, position);
	}

	function isValidConnection(connection: Connection): boolean {
		if (connection.source === connection.target) return false;
		const source = nodes.find((n) => n.id === connection.source);
		const target = nodes.find((n) => n.id === connection.target);
		if (!source || !target) return false;
		if (source.data.nodeType === 'end' || target.data.nodeType === 'start') return false;
		if (edges.some((e) => e.source === connection.source && e.target === connection.target))
			return false;
		return true;
	}

	function handleConnect(connection: Connection) {
		const domain = {
			id: crypto.randomUUID(),
			source: connection.source,
			target: connection.target,
			label: '',
			priority: edges.filter((e) => e.source === connection.source).length,
			condition_groups: []
		};
		// SvelteFlow already appended a default edge for this connection; replace
		// it with ours so the id is the persisted client UUID.
		edges = edges.map((e) =>
			e.source === connection.source && e.target === connection.target && !e.data?.domain
				? toFlowEdge(domain)
				: e
		);
		selectedEdgeId = domain.id;
		selectedNodeId = null;
		markDirty();
	}

	function deleteNode(id: string) {
		nodes = nodes.filter((n) => n.id !== id);
		edges = edges.filter((e) => e.source !== id && e.target !== id);
		if (selectedNodeId === id) selectedNodeId = null;
		markDirty();
	}

	function addVariable(key: string, type: string) {
		if (variables.some((v) => v.key === key)) return;
		variables = [...variables, { id: crypto.randomUUID(), key, type, default_value: null }];
		markDirty();
	}

	function removeVariable(id: string) {
		variables = variables.filter((v) => v.id !== id);
		// Strip conditions that referenced it so the save doesn't 400.
		for (const edge of edges) {
			const groups = edge.data?.domain?.condition_groups ?? [];
			for (const group of groups) {
				group.conditions = group.conditions.filter((c: any) => c.variable !== id);
			}
			edge.data!.domain.condition_groups = groups.filter(
				(g: any) => g.conditions.length || g.children?.length
			);
		}
		refreshVisuals();
		markDirty();
	}

	function handleInspectorChange() {
		refreshVisuals();
		markDirty();
	}

	// ---------- secrets ----------

	let secrets = $state<any[]>([]);

	async function refreshSecrets() {
		const res = await fetch(opsUrl('list-secrets'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({})
		});
		if (!res.ok) return;
		const data = await res.json().catch(() => null);
		secrets = Array.isArray(data) ? data : (data?.results ?? []);
	}

	async function addSecret(name: string, value: string) {
		const res = await fetch(opsUrl('create-secret'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, value, folder: folderId })
		});
		if (res.ok) await refreshSecrets();
	}

	async function removeSecret(id: string) {
		const res = await fetch(opsUrl('delete-secret'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ id })
		});
		if (res.ok) await refreshSecrets();
	}

	$effect(() => {
		if (!readonly) refreshSecrets();
	});

	setContext('workflowEditor', {
		get readonly() {
			return readonly;
		},
		deleteNode
	});

	// Track app dark mode (`.dark` on <html>) so SvelteFlow follows the theme.
	let isDark = $state(false);
	$effect(() => {
		const root = document.documentElement;
		const update = () => (isDark = root.classList.contains('dark'));
		update();
		const observer = new MutationObserver(update);
		observer.observe(root, { attributes: true, attributeFilter: ['class'] });
		return () => observer.disconnect();
	});

	const hasStart = $derived(nodes.some((n) => n.data.nodeType === 'start'));

	function focusError(nodeError: any) {
		if (!nodeError.node_id) return;
		selectedNodeId = nodeError.node_id;
		selectedEdgeId = null;
		flowInstance?.fitView({ nodes: [{ id: nodeError.node_id }], duration: 300, maxZoom: 1.2 });
	}
</script>

<div
	class="flex h-full bg-surface-50-950 rounded-base overflow-hidden border border-surface-200-800"
>
	{#if !readonly}
		<Palette
			{hasStart}
			{variables}
			{secrets}
			onAdd={addNode}
			onAddVariable={addVariable}
			onRemoveVariable={removeVariable}
			onAddSecret={addSecret}
			onRemoveSecret={removeSecret}
		/>
	{/if}

	<div class="flex-1 min-w-0 min-h-0 flex flex-col">
		<div class="flex-1 min-h-0 relative">
			<SvelteFlow
				bind:nodes
				bind:edges
				colorMode={isDark ? 'dark' : 'light'}
				{nodeTypes}
				isValidConnection={readonly ? () => false : isValidConnection}
				onconnect={readonly ? undefined : handleConnect}
				onnodedragstop={readonly ? undefined : markDirty}
				ondelete={readonly ? undefined : markDirty}
				onnodeclick={({ node }) => {
					selectedNodeId = node.id;
					selectedEdgeId = null;
				}}
				onedgeclick={({ edge }) => {
					selectedEdgeId = edge.id;
					selectedNodeId = null;
				}}
				onpaneclick={() => {
					selectedNodeId = null;
					selectedEdgeId = null;
				}}
				ondragover={readonly ? undefined : handleDragOver}
				ondrop={readonly ? undefined : handleDrop}
				nodesDraggable={!readonly}
				nodesConnectable={!readonly}
				elementsSelectable={true}
				oninit={handleFlowInit}
				snapGrid={[10, 10]}
				minZoom={0.2}
				proOptions={{ hideAttribution: true }}
				defaultEdgeOptions={{ markerEnd: EDGE_MARKER, style: EDGE_STYLE }}
			>
				<Background variant={BackgroundVariant.Dots} gap={20} />
				<Controls showLock={false} />
				<MiniMap />

				<Panel position="top-right">
					<div class="flex items-center gap-2">
						<button
							type="button"
							class="btn preset-tonal text-sm"
							class:preset-filled-secondary-500={runsOpen}
							onclick={() => (runsOpen = !runsOpen)}
							data-testid="toggle-runs"
						>
							<i class="fa-solid fa-list-check mr-1"></i>
							{m.workflowRuns()}
						</button>
						<button
							type="button"
							class="btn preset-tonal text-sm"
							disabled={running}
							onclick={runWorkflow}
							data-testid="run-workflow"
						>
							{#if running}
								<i class="fa-solid fa-spinner fa-spin mr-1"></i>
							{:else}
								<i class="fa-solid fa-play mr-1"></i>
							{/if}
							{m.runWorkflow()}
						</button>
						{#if !readonly}
							{#if saveState === 'saving' || saveState === 'dirty'}
								<span class="text-xs text-surface-500 flex items-center gap-1">
									<i class="fa-solid fa-spinner fa-spin"></i>
									{m.graphSaving()}
								</span>
							{:else if saveState === 'saved'}
								<span class="text-xs text-success-600 flex items-center gap-1">
									<i class="fa-solid fa-check"></i>
									{m.graphSaved()}
								</span>
							{:else if saveState === 'error'}
								<button
									type="button"
									class="text-xs text-error-500 flex items-center gap-1 cursor-pointer"
									title={saveError}
									onclick={save}
								>
									<i class="fa-solid fa-triangle-exclamation"></i>
									{saveError}
								</button>
							{/if}
							<button
								type="button"
								class="btn preset-filled-primary-500 text-sm"
								disabled={publishing || saveState === 'saving'}
								onclick={publish}
								data-testid="publish-workflow"
							>
								{#if publishing}
									<i class="fa-solid fa-spinner fa-spin mr-1"></i>
								{:else}
									<i class="fa-solid fa-rocket mr-1"></i>
								{/if}
								{m.publishWorkflow()}
							</button>
						{:else}
							<button
								type="button"
								class="btn preset-filled-primary-500 text-sm"
								onclick={newDraft}
								data-testid="new-draft"
							>
								<i class="fa-solid fa-pen mr-1"></i>
								{m.newDraft()}
							</button>
						{/if}
					</div>
				</Panel>

				{#if validationErrors.length}
					<Panel position="bottom-right">
						<div
							class="w-72 max-h-56 overflow-y-auto rounded-base border border-error-300 dark:border-error-700 bg-surface-50-950 shadow-lg"
						>
							<p
								class="px-3 py-2 text-xs font-semibold text-error-600 border-b border-surface-200-800"
							>
								<i class="fa-solid fa-triangle-exclamation mr-1"></i>
								{m.publishValidationFailed()}
							</p>
							<ul>
								{#each validationErrors as validationError}
									<li>
										<button
											type="button"
											class="w-full text-left px-3 py-1.5 text-xs text-surface-800-200 hover:bg-surface-100-900 cursor-pointer"
											onclick={() => focusError(validationError)}
										>
											{validationError.message}
										</button>
									</li>
								{/each}
							</ul>
						</div>
					</Panel>
				{/if}
			</SvelteFlow>
		</div>

		{#if runsOpen}
			<RunsPanel bind:this={runsPanel} {workflowId} />
		{/if}
	</div>

	<Inspector
		selectedNode={readonly ? null : selectedNode}
		selectedEdge={readonly ? null : selectedEdge}
		{variables}
		{roles}
		{actors}
		{taskTemplates}
		{subprocessCandidates}
		{creatableModels}
		{fkOptions}
		{hookUrl}
		onChange={handleInspectorChange}
	/>
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
	:global(.svelte-flow .svelte-flow__edge:hover .svelte-flow__edge-path) {
		stroke: var(--color-secondary-300);
		stroke-width: 3;
		cursor: pointer;
	}
	:global(.svelte-flow .svelte-flow__edge.selected .svelte-flow__edge-path) {
		stroke: var(--color-primary-500);
		stroke-width: 3;
	}
	:global(.svelte-flow .svelte-flow__edge-textbg) {
		fill: var(--color-surface-50);
	}
	:global(.dark .svelte-flow .svelte-flow__edge-textbg) {
		fill: var(--color-surface-950);
	}
	:global(.svelte-flow .svelte-flow__edge-text) {
		fill: var(--color-surface-700);
		font-size: 10px;
	}
	:global(.dark .svelte-flow .svelte-flow__edge-text) {
		fill: var(--color-surface-300);
	}
</style>
