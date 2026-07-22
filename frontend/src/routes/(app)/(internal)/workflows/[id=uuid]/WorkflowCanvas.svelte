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
	import TriggersPanel from './TriggersPanel.svelte';
	import StepNode from './nodes/StepNode.svelte';
	import TerminalNode from './nodes/TerminalNode.svelte';
	import TriggerNode, { TRIGGER_ICONS } from './nodes/TriggerNode.svelte';

	interface Props {
		graph: any;
		workflowId: string;
		versionId: string;
		versionStatus: string;
		folderId: string;
		readonly: boolean;
		roles: any[];
		actors: any[];
		taskTemplates: any[];
		subprocessCandidates: any[];
		creatableModels?: any[];
		fkOptions?: Record<string, any[]>;
		onDraftCreated?: (draft: { id: string; version_number: number }) => void;
	}

	let {
		graph,
		workflowId,
		versionId,
		versionStatus,
		folderId,
		readonly,
		roles,
		actors,
		taskTemplates,
		subprocessCandidates,
		creatableModels = [],
		fkOptions = {},
		onDraftCreated
	}: Props = $props();

	// A published version is directly editable: the first save transparently
	// clones it into a draft (ensureDraft) and edits continue there.
	let activeVersionId = $state(versionId);
	let status = $state(versionStatus);

	function opsUrl(action: string) {
		return `/workflows/${workflowId}/ops?action=${action}`;
	}

	const nodeTypes = { step: StepNode, terminal: TerminalNode, trigger: TriggerNode };

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
			case 'trigger': {
				const config = domain.trigger_config ?? {};
				switch (config.type) {
					case 'schedule':
						return config.cron_expression || null;
					case 'internal_event':
						return config.event_key || null;
					case 'webhook':
						return 'webhook';
					default:
						return null;
				}
			}
			default:
				return null;
		}
	}

	const NODE_TYPE_LABELS: Record<string, () => string> = {
		trigger: m.workflowNodeTrigger,
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
			triggerType:
				domain.type === 'trigger' ? (domain.trigger_config?.type ?? 'manual') : undefined,
			registration:
				domain.type === 'trigger' && domain.ref ? (registrationsByRef[domain.ref] ?? null) : null,
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
			type: domain.type === 'end' ? 'terminal' : domain.type === 'trigger' ? 'trigger' : 'step',
			position,
			draggable: !readonly,
			deletable: !readonly,
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

	// ---------- trigger registrations (operational state, exists after publish) ----------

	let registrations = $state<any[]>([]);
	const registrationsByRef = $derived(
		Object.fromEntries(registrations.map((r: any) => [r.node_ref, r]))
	);

	async function refreshRegistrations() {
		const res = await fetch(opsUrl('list-triggers'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ workflow: workflowId })
		});
		if (!res.ok) return;
		const data = await res.json().catch(() => null);
		registrations = Array.isArray(data) ? data : (data?.results ?? []);
		// Node visuals carry the registration (armed/disarmed dot); rebuild them.
		refreshVisuals();
	}

	let variables = $state<any[]>(graph.variables ?? []);
	let nodes = $state<Node[]>((graph.nodes ?? []).map(toFlowNode));
	let edges = $state<Edge[]>((graph.edges ?? []).map(toFlowEdge));

	// A brand-new draft gets a manual trigger and an end waiting to be wired,
	// instead of an empty void.
	if (!readonly && nodes.length === 0) {
		nodes = [
			toFlowNode(newNodeDomain('trigger', { x: 120, y: 202 }, 'manual'), 0),
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
		clearRunView();
		saveState = 'dirty';
		validationErrors = [];
		if (saveTimer) clearTimeout(saveTimer);
		saveTimer = setTimeout(save, 1200);
	}

	// ---------- reference run for the data browser (spec D20) ----------

	let referenceRun = $state<any | null>(null);
	let referencePinned = $state(false);
	let referenceFetchInFlight = false;

	function pickReference(runs: any[]) {
		return (
			runs.find(
				(run: any) => run.status === 'completed' && Object.keys(run.node_outputs ?? {}).length
			) ??
			runs.find((run: any) => Object.keys(run.node_outputs ?? {}).length) ??
			null
		);
	}

	async function ensureReferenceRun() {
		if (referenceRun || referenceFetchInFlight) return;
		referenceFetchInFlight = true;
		try {
			const res = await fetch(opsUrl('list-instances'), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ workflow: workflowId })
			});
			if (!res.ok) return;
			const data = await res.json();
			referenceRun = pickReference(data.results ?? data);
		} finally {
			// Deliberately no "already attempted" latch: while no run has data
			// yet, every node selection retries, and the runs-panel poll below
			// picks new runs up live.
			referenceFetchInFlight = false;
		}
	}

	function pinReference(run: any) {
		referencePinned = true;
		referenceRun = run;
	}

	// Runs-panel polling feeds this: without an explicit pin, the reference
	// follows the latest run with data, so the browser populates live.
	function handleRunsRefreshed(runs: any[]) {
		if (referencePinned) return;
		const candidate = pickReference(runs);
		if (candidate && candidate.id !== referenceRun?.id) {
			referenceRun = candidate;
		}
	}

	$effect(() => {
		if (selectedNodeId && !readonly) ensureReferenceRun();
	});

	// Upstream nodes only: data available TO the selected node.
	const ancestorNodeIds = $derived.by(() => {
		if (!selectedNodeId) return new Set<string>();
		const incoming = new Map<string, string[]>();
		for (const e of edges) {
			incoming.set(e.target, [...(incoming.get(e.target) ?? []), e.source]);
		}
		const seen = new Set<string>();
		const stack = [...(incoming.get(selectedNodeId) ?? [])];
		while (stack.length) {
			const id = stack.pop()!;
			if (seen.has(id)) continue;
			seen.add(id);
			stack.push(...(incoming.get(id) ?? []));
		}
		return seen;
	});

	const referenceNodes = $derived.by(() => {
		if (!referenceRun) return [];
		const outputs = referenceRun.node_outputs ?? {};
		return nodes
			.filter((n) => ancestorNodeIds.has(n.id))
			.map((n) => {
				const domain: any = n.data.domain;
				const key = domain.ref || domain.id;
				return { key, label: String(n.data.label), output: outputs[key] };
			})
			.filter((entry) => entry.output !== undefined);
	});

	const referenceVariables = $derived.by(() => {
		if (!referenceRun) return {};
		return referenceRun.variables ?? {};
	});

	// ---------- run visualization ----------

	type RunState = 'visited' | 'active' | 'error';
	interface RunView {
		runId: string;
		nodeStates: Record<string, RunState>;
		edgeIds: Set<string>;
		replaying: boolean;
	}
	let runView = $state<RunView | null>(null);
	let replayTimer: ReturnType<typeof setTimeout> | null = null;

	const TRAVERSED_EDGE_STYLE = 'stroke: var(--color-success-400); stroke-width: 2.5;';

	function markVisited(nodeId: string, view: RunView) {
		if (!view.nodeStates[nodeId]) view.nodeStates[nodeId] = 'visited';
		for (const edge of edges) {
			if (edge.target === nodeId && view.nodeStates[edge.source]) {
				view.edgeIds.add(edge.id);
			}
		}
	}

	function applyRunView(currentNodeId: string | null = null) {
		nodes = nodes.map((n) => ({
			...n,
			data: {
				...n.data,
				runState: currentNodeId === n.id ? 'active' : (runView?.nodeStates[n.id] ?? null)
			}
		}));
		edges = edges.map((e) => {
			const traversed = runView?.edgeIds.has(e.id) ?? false;
			return {
				...e,
				animated: traversed,
				style: traversed ? TRAVERSED_EDGE_STYLE : EDGE_STYLE
			};
		});
	}

	function visitedSteps(logs: any[]) {
		return logs.filter((entry) => entry.event_type === 'node_entered' && entry.node?.id);
	}

	function showRun(run: any, logs: any[]) {
		stopReplay();
		runView = {
			runId: run.id,
			nodeStates: {},
			edgeIds: new Set(),
			replaying: false
		};
		for (const step of visitedSteps(logs)) markVisited(step.node.id, runView);
		for (const active of run.active_nodes ?? []) {
			runView.nodeStates[active.id] = active.status === 'error' ? 'error' : 'active';
		}
		applyRunView();
	}

	function replayRun(run: any, logs: any[]) {
		stopReplay();
		const steps = visitedSteps(logs);
		if (!steps.length) return showRun(run, logs);
		runView = { runId: run.id, nodeStates: {}, edgeIds: new Set(), replaying: true };
		applyRunView();
		let index = 0;
		const tick = () => {
			if (!runView) return;
			if (index >= steps.length) {
				showRun(run, logs);
				return;
			}
			const nodeId = steps[index].node.id;
			markVisited(nodeId, runView);
			applyRunView(nodeId);
			index += 1;
			replayTimer = setTimeout(tick, 650);
		};
		tick();
	}

	function stopReplay() {
		if (replayTimer) clearTimeout(replayTimer);
		replayTimer = null;
	}

	function clearRunView() {
		if (!runView) return;
		stopReplay();
		runView = null;
		applyRunView();
	}

	$effect(() => () => stopReplay());

	function refreshVisuals() {
		nodes = nodes.map((n) => ({
			...n,
			data: {
				...visualData(n.data.domain, n.data.error ?? null),
				runState: n.data.runState ?? null
			}
		}));
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
		if (status === 'published' && !(await ensureDraft())) return false;
		const res = await fetch(opsUrl('save-graph'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ version: activeVersionId, graph: serializeGraph() })
		});
		if (!res.ok) {
			const body = await res.json().catch(() => ({}));
			saveError = body.error ?? body.detail ?? res.statusText;
			saveState = 'error';
			return false;
		}
		// The backend assigns refs to new nodes; sync them so run-by-trigger and
		// the webhook inspector work without a reload.
		const document = await res.json().catch(() => null);
		if (Array.isArray(document?.nodes)) {
			const refsById = new Map(document.nodes.map((n: any) => [n.id, n.ref]));
			for (const node of nodes) {
				const domain: any = node.data.domain;
				if (!domain.ref && refsById.get(domain.id)) domain.ref = refsById.get(domain.id);
			}
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
				body: JSON.stringify({ version: activeVersionId })
			});
			if (res.ok) {
				await refreshRegistrations();
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

	async function ensureDraft(): Promise<boolean> {
		const res = await fetch(opsUrl('new-draft'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ version: activeVersionId })
		});
		if (!res.ok) {
			const body = await res.json().catch(() => ({}));
			saveError =
				body.error === 'draftAlreadyExists'
					? m.draftAlreadyExistsReload()
					: (body.error ?? res.statusText);
			saveState = 'error';
			return false;
		}
		const draft = await res.json();
		// The server clone has fresh row ids; the canvas keeps ITS state as the
		// source of truth (the next save wholesale-replaces the clone), so re-id
		// everything locally to avoid colliding with the published rows.
		remapGraphIds();
		activeVersionId = draft.id;
		status = 'draft';
		onDraftCreated?.(draft);
		return true;
	}

	function remapGraphIds() {
		const idMap = new Map<string, string>();
		const fresh = (old: string) => {
			if (!idMap.has(old)) idMap.set(old, crypto.randomUUID());
			return idMap.get(old)!;
		};
		const remapGroup = (group: any): any => ({
			...group,
			conditions: (group.conditions ?? []).map((c: any) => ({
				...c,
				variable: fresh(c.variable)
			})),
			children: (group.children ?? []).map(remapGroup)
		});
		variables = variables.map((v) => ({ ...v, id: fresh(v.id) }));
		nodes = nodes.map((n) => {
			const domain: any = { ...(n.data.domain as any), id: fresh(n.id) };
			return { ...n, id: domain.id, data: { ...n.data, domain } };
		});
		edges = edges.map((e) => {
			const domain: any = { ...(e.data!.domain as any) };
			domain.id = fresh(e.id);
			domain.source = fresh(e.source);
			domain.target = fresh(e.target);
			if (domain.condition_groups) {
				domain.condition_groups = domain.condition_groups.map(remapGroup);
			}
			return {
				...e,
				id: domain.id,
				source: domain.source,
				target: domain.target,
				data: { ...e.data, domain }
			};
		});
		if (selectedNodeId) selectedNodeId = idMap.get(selectedNodeId) ?? null;
		if (selectedEdgeId) selectedEdgeId = idMap.get(selectedEdgeId) ?? null;
	}

	let runsOpen = $state(false);
	let runsPanel = $state<RunsPanel | null>(null);
	let triggersOpen = $state(false);
	let running = $state(false);
	let runPickerOpen = $state(false);

	const triggerNodes = $derived(nodes.filter((n) => n.data.nodeType === 'trigger'));

	async function startRun(entryNodeRef: string | null) {
		runPickerOpen = false;
		running = true;
		try {
			// Flush pending edits, but never auto-draft a pristine published
			// version just because it was run.
			const pending = saveState === 'dirty' || saveState === 'saving' || saveState === 'error';
			if (!readonly && pending && !(await save())) return;
			const res = await fetch(opsUrl('run'), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					version: activeVersionId,
					...(entryNodeRef ? { entry_node_ref: entryNodeRef } : {})
				})
			});
			if (res.ok) {
				runsOpen = true;
				await runsPanel?.refresh();
			}
		} finally {
			running = false;
		}
	}

	// Manual trigger present → fire it; exactly one trigger → fire it; else the
	// entry is ambiguous (the backend would 400) → offer a picker.
	async function runWorkflow() {
		const manual = triggerNodes.find(
			(n) => (n.data.domain as any)?.trigger_config?.type === 'manual'
		);
		if (manual) return startRun((manual.data.domain as any).ref ?? null);
		if (triggerNodes.length <= 1) {
			return startRun(((triggerNodes[0]?.data.domain as any)?.ref as string) ?? null);
		}
		runPickerOpen = !runPickerOpen;
	}

	// ---------- graph edits ----------

	function newNodeDomain(type: string, position?: { x: number; y: number }, triggerType?: string) {
		let trigger_config: Record<string, unknown> = {};
		if (type === 'trigger') {
			trigger_config = { type: triggerType ?? 'manual' };
			if (triggerType === 'schedule') {
				trigger_config = { ...trigger_config, cron_expression: '', timezone: 'UTC' };
			} else if (triggerType === 'internal_event') {
				trigger_config = { ...trigger_config, event_key: '', filters: {} };
			}
		}
		return {
			id: crypto.randomUUID(),
			type,
			label: '',
			fork_type: 'exclusive',
			join_type: 'none',
			task_template: null,
			subprocess_workflow: null,
			action_config: type === 'action' ? { type: 'log' } : {},
			trigger_config,
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

	function addNode(type: string, triggerType?: string, position?: { x: number; y: number }) {
		// At most one manual trigger per graph (its entry would be ambiguous).
		if (
			type === 'trigger' &&
			triggerType === 'manual' &&
			nodes.some(
				(n) =>
					n.data.nodeType === 'trigger' && (n.data.domain as any)?.trigger_config?.type === 'manual'
			)
		) {
			return;
		}
		const fallback = { x: 200 + Math.random() * 80, y: 160 + Math.random() * 80 };
		const domain = newNodeDomain(type, position ?? fallback, triggerType);
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
		const raw = event.dataTransfer?.getData('application/ciso-workflow-node');
		if (!raw) return;
		let payload: { type?: string; triggerType?: string };
		try {
			payload = JSON.parse(raw);
		} catch {
			return;
		}
		if (!payload.type) return;
		event.preventDefault();
		const position = flowInstance?.screenToFlowPosition({
			x: event.clientX,
			y: event.clientY
		});
		addNode(payload.type, payload.triggerType, position);
	}

	function isValidConnection(connection: Connection): boolean {
		if (connection.source === connection.target) return false;
		const source = nodes.find((n) => n.id === connection.source);
		const target = nodes.find((n) => n.id === connection.target);
		if (!source || !target) return false;
		if (source.data.nodeType === 'end' || target.data.nodeType === 'trigger') return false;
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

	$effect(() => {
		refreshRegistrations();
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
						<a
							href={`/workflows/${workflowId}/export-yaml`}
							class="btn preset-tonal text-sm"
							title={m.exportWorkflowYaml()}
							aria-label={m.exportWorkflowYaml()}
							data-testid="export-workflow-yaml"
						>
							<i class="fa-solid fa-download"></i>
						</a>
						<button
							type="button"
							class="btn preset-tonal text-sm"
							class:preset-filled-secondary-500={triggersOpen}
							onclick={() => (triggersOpen = !triggersOpen)}
							data-testid="toggle-triggers"
						>
							<i class="fa-solid fa-bolt mr-1"></i>
							{m.workflowTriggers()}
						</button>
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
						<div class="relative">
							<button
								type="button"
								class="btn preset-tonal text-sm"
								class:preset-filled-secondary-500={runPickerOpen}
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
							{#if runPickerOpen}
								<div
									class="absolute right-0 top-full mt-1 z-10 w-60 rounded-base border border-surface-200-800 bg-surface-50-950 shadow-lg"
									data-testid="run-trigger-picker"
								>
									<p
										class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-surface-500 border-b border-surface-200-800"
									>
										{m.chooseTriggerToRun()}
									</p>
									<ul>
										{#each triggerNodes as triggerNode (triggerNode.id)}
											{@const domain = triggerNode.data.domain as any}
											<li>
												<button
													type="button"
													class="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-surface-800-200 hover:bg-surface-100-900 cursor-pointer text-left"
													onclick={() => startRun(domain.ref ?? null)}
												>
													<i
														class="fa-solid {TRIGGER_ICONS[domain.trigger_config?.type] ??
															'fa-bolt'} w-4 text-center text-surface-500"
													></i>
													<span class="truncate">{triggerNode.data.label}</span>
													{#if domain.ref}
														<span class="ml-auto font-mono text-[9px] text-surface-500 shrink-0">
															{domain.ref}
														</span>
													{/if}
												</button>
											</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
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
							{#if status === 'draft'}
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
							{/if}
						{/if}
					</div>
				</Panel>

				{#if runView}
					<Panel position="top-center">
						<button
							type="button"
							class="btn preset-tonal text-xs shadow-md"
							title={m.exitRunView()}
							onclick={clearRunView}
							data-testid="exit-run-view"
						>
							<i class="fa-solid fa-clock-rotate-left mr-1 text-success-500"></i>
							{String(runView.runId).slice(0, 8)}
							{#if runView.replaying}
								<i class="fa-solid fa-circle-notch fa-spin ml-1"></i>
							{/if}
							<i class="fa-solid fa-xmark ml-2"></i>
						</button>
					</Panel>
				{/if}

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

		{#if triggersOpen}
			<TriggersPanel {registrations} {workflowId} onRefresh={refreshRegistrations} />
		{/if}

		{#if runsOpen}
			<RunsPanel
				bind:this={runsPanel}
				{workflowId}
				onShowRun={showRun}
				onReplayRun={replayRun}
				onPinReference={pinReference}
				onRunsRefreshed={handleRunsRefreshed}
				referenceRunId={referenceRun?.id ?? null}
			/>
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
		{workflowId}
		{registrationsByRef}
		onRegistrationsChanged={refreshRegistrations}
		referenceRunId={referenceRun?.id ?? null}
		{referenceVariables}
		{referenceNodes}
		secretNames={secrets.map((s: any) => s.name)}
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
