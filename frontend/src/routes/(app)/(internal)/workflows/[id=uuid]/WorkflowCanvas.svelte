<script lang="ts">
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { setContext } from 'svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import {
		SvelteFlow,
		useSvelteFlow,
		Controls,
		ControlButton,
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
	import { computeLayout } from './graph-layout';

	import Palette from './Palette.svelte';
	import Inspector from './Inspector.svelte';
	import RunsPanel from './RunsPanel.svelte';
	import TriggersPanel from './TriggersPanel.svelte';
	import WorkflowDataPanel from './WorkflowDataPanel.svelte';
	import StepNode from './nodes/StepNode.svelte';
	import ConditionNode from './nodes/ConditionNode.svelte';
	import TerminalNode from './nodes/TerminalNode.svelte';
	import TriggerNode, { TRIGGER_ICONS } from './nodes/TriggerNode.svelte';

	interface Props {
		graph: any;
		workflowName: string;
		workflowDescription?: string | null;
		initialVersionNumber: number;
		workflowId: string;
		versionId: string;
		versionStatus: string;
		folderId: string;
		readonly: boolean;
		hasPublishedFallback?: boolean;
		onDiscarded?: () => void;
		taskTemplates: any[];
		subprocessCandidates: any[];
		creatableModels?: any[];
		readableModels?: any[];
		fkOptions?: Record<string, any[]>;
	}

	let {
		graph,
		workflowName,
		workflowDescription = null,
		initialVersionNumber,
		workflowId,
		versionId,
		versionStatus,
		folderId,
		readonly,
		hasPublishedFallback = false,
		onDiscarded,
		taskTemplates,
		subprocessCandidates,
		creatableModels = [],
		readableModels = [],
		fkOptions = {}
	}: Props = $props();

	// A published version is directly editable: the first save transparently
	// clones it into a draft (ensureDraft) and edits continue there.
	let activeVersionId = $state(versionId);
	let status = $state(versionStatus);
	let versionNumber = $state(initialVersionNumber);

	const STATUS_BADGE: Record<string, { class: string; label: () => string }> = {
		draft: { class: 'preset-tonal-warning', label: () => m.draftVersion() },
		published: { class: 'preset-tonal-success', label: () => m.publishedVersion() },
		archived: { class: 'preset-tonal', label: () => m.archivedVersion() }
	};
	const badge = $derived(STATUS_BADGE[status] ?? STATUS_BADGE.archived);

	const modalStore: ModalStore = getModalStore();

	function opsUrl(action: string) {
		return `/workflows/${workflowId}/ops?action=${action}`;
	}

	const nodeTypes = {
		step: StepNode,
		condition: ConditionNode,
		terminal: TerminalNode,
		trigger: TriggerNode
	};

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
					case 'read_objects':
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
			forEach: domain.type === 'action' && !!domain.action_config?.for_each,
			branches: domain.type === 'condition' ? conditionBranchVisuals(domain) : undefined,
			triggerType:
				domain.type === 'trigger' ? (domain.trigger_config?.type ?? 'manual') : undefined,
			registration:
				domain.type === 'trigger' && domain.ref ? (registrationsByRef[domain.ref] ?? null) : null,
			error,
			domain
		};
	}

	// A short human-readable summary of a branch's conditions, used as the
	// display name fallback (node port label / Inspector placeholder).
	function conditionSummary(branch: any): string {
		const conditions = branch.condition_groups?.[0]?.conditions ?? [];
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

	function edgeLabel(domain: any): string {
		return domain.label || '';
	}

	function isConditionNodeId(nodeId: string): boolean {
		return (nodes.find((n) => n.id === nodeId)?.data?.domain as any)?.type === 'condition';
	}

	// The set of branch ids that currently have a wire (an edge whose
	// source_branch references them). Drives the node's wired/unwired ports.
	function wiredBranchIds(): Set<string> {
		return new Set(
			edges.map((e) => (e.data?.domain as any)?.source_branch).filter(Boolean) as string[]
		);
	}

	// Branches sorted for display/evaluation: conditional branches first by
	// order, the single default (is_default) pinned last regardless of its
	// order value.
	function sortedBranches(domain: any): any[] {
		return [...(domain.branches ?? [])].sort(
			(a, b) => Number(!!a.is_default) - Number(!!b.is_default) || (a.order ?? 0) - (b.order ?? 0)
		);
	}

	// Per-port descriptors the condition node renders: one per branch, in
	// display order, carrying its wired state so unwired ports stay connectable.
	function conditionBranchVisuals(domain: any) {
		const wired = wiredBranchIds();
		return sortedBranches(domain).map((branch) => ({
			branchId: branch.id,
			name: branch.name || conditionSummary(branch),
			isDefault: !!branch.is_default,
			wired: wired.has(branch.id)
		}));
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
			type:
				domain.type === 'end'
					? 'terminal'
					: domain.type === 'trigger' || domain.type === 'condition'
						? domain.type
						: 'step',
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
			// An edge leaving a condition node anchors to its branch's port; the
			// handle id on a condition node IS the branch id.
			sourceHandle: domain.source_branch ?? undefined,
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
	// Edges are declared (empty) before nodes so visualData's branch lookup can
	// read them during the initial node mapping, and filled right after so
	// toFlowEdge can resolve source node types. The refreshVisuals() below then
	// backfills condition branch rows once both exist.
	let edges = $state<Edge[]>([]);
	let nodes = $state<Node[]>((graph.nodes ?? []).map(toFlowNode));
	edges = (graph.edges ?? []).map(toFlowEdge);

	// A brand-new draft gets a manual trigger and an end waiting to be wired,
	// instead of an empty void.
	if (!readonly && nodes.length === 0) {
		nodes = [
			toFlowNode(newNodeDomain('trigger', { x: 120, y: 202 }, 'manual'), 0),
			toFlowNode(newNodeDomain('end', { x: 560, y: 202 }), 1)
		];
	}
	refreshVisuals();

	// ---------- auto-layout (dagre) ----------
	// Node movement strategy (empirically validated via the Playwright edge
	// harness): REPLACE node objects. New identities make xyflow recompute
	// positionAbsolute (identity-preserving mutation leaves it stale — nodes
	// only snap into place on click); handleBounds survive replacement since
	// `measured` rides the spread. The historical vanishing-edge bug was
	// remapGraphIds leaving stale branch ids in data.branches, not this.

	function applyLayout() {
		const positions = computeLayout(nodes, edges);
		nodes = nodes.map((node) => {
			const position = positions.get(node.id);
			return position ? { ...node, position } : node;
		});
		setTimeout(() => flowInstance?.fitView({ duration: 300, padding: 0.15, maxZoom: 1 }), 50);
	}

	function tidyUp() {
		applyLayout();
		// Through the usual funnel: tidy-up autosaves and is undoable with ⌘Z.
		markDirty();
	}

	// Graphs that arrive without positions (imported or hand-written YAML) get
	// laid out once nodes are measured, so dagre works with real dimensions.
	// Drafts persist the result via the autosave; published views stay
	// visual-only (saving would auto-draft a pristine version just for layout).
	let pendingInitialLayout = (graph.nodes ?? []).some(
		(n: any) => n.position?.x === undefined && n.position?.y === undefined
	);
	$effect(() => {
		if (!pendingInitialLayout || nodes.length === 0) return;
		if (!nodes.every((n) => n.measured?.width)) return;
		pendingInitialLayout = false;
		applyLayout();
		if (!readonly && status === 'draft') markDirty();
	});

	// ---------- undo/redo ----------

	// Snapshot-based history hooked into markDirty (the single funnel every
	// graph mutation goes through). Docs are plain (non-$state) deep clones of
	// serializeGraph() output; only the stack sizes are reactive, for the
	// header buttons' disabled states. Secrets are server-side and never part
	// of the graph doc, so they are never snapshotted.
	type Doc = { nodes: any[]; edges: any[]; variables: any[] };
	let undoStack: Doc[] = [];
	let redoStack: Doc[] = [];
	let historySizes = $state({ undo: 0, redo: 0 });
	let lastSnapshot: Doc; // state as of the LAST capture
	let lastPushAt = 0;
	let restoring = false;
	const HISTORY_LIMIT = 50;
	const COALESCE_MS = 800;

	// $state.snapshot unwraps the $state proxies nested in the domain objects
	// (structuredClone alone would throw on them) and deep-clones everything.
	function takeSnapshot(): Doc {
		return $state.snapshot(serializeGraph()) as Doc;
	}
	lastSnapshot = takeSnapshot();

	function syncHistorySizes() {
		historySizes = { undo: undoStack.length, redo: redoStack.length };
	}

	function applyDoc(doc: Doc) {
		restoring = true;
		// Defeat coalescing for the next real edit: it must push a fresh undo
		// step (and clear the redo stack) even right after an undo/redo.
		lastPushAt = 0;
		try {
			// Clone before mapping into live state: the live domain objects get
			// mutated in place by the Inspector, and the doc also stays on a stack.
			variables = structuredClone(doc.variables);
			nodes = structuredClone(doc.nodes).map(toFlowNode);
			edges = structuredClone(doc.edges).map(toFlowEdge);
			if (selectedNodeId && !nodes.some((n) => n.id === selectedNodeId)) selectedNodeId = null;
			if (selectedEdgeId && !edges.some((e) => e.id === selectedEdgeId)) selectedEdgeId = null;
			refreshVisuals();
			markDirty(); // reuse the debounce/save path; restoring=true skips the snapshot block
		} finally {
			restoring = false;
		}
	}

	function undo() {
		if (!undoStack.length) return;
		redoStack.push(lastSnapshot);
		const doc = undoStack.pop()!;
		lastSnapshot = doc;
		syncHistorySizes();
		applyDoc(doc);
	}

	function redo() {
		if (!redoStack.length) return;
		undoStack.push(lastSnapshot);
		const doc = redoStack.pop()!;
		lastSnapshot = doc;
		syncHistorySizes();
		applyDoc(doc);
	}

	// ⌘/Ctrl+Z undo, ⇧⌘/Ctrl+Z redo (plus Ctrl+Y). Text controls keep their
	// native text undo: events targeting them are left alone.
	$effect(() => {
		if (readonly) return;
		const handleKeydown = (event: KeyboardEvent) => {
			if (!(event.metaKey || event.ctrlKey)) return;
			const key = event.key.toLowerCase();
			const isZ = key === 'z';
			const isY = key === 'y' && event.ctrlKey;
			if (!isZ && !isY) return;
			const target = (event.target ?? document.activeElement) as HTMLElement | null;
			if (
				target &&
				(target.tagName === 'INPUT' ||
					target.tagName === 'TEXTAREA' ||
					target.tagName === 'SELECT' ||
					target.isContentEditable)
			) {
				return;
			}
			event.preventDefault();
			if (isY || event.shiftKey) redo();
			else undo();
		};
		window.addEventListener('keydown', handleKeydown);
		return () => window.removeEventListener('keydown', handleKeydown);
	});

	// ---------- selection ----------

	let selectedNodeId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	const selectedNode = $derived(nodes.find((n) => n.id === selectedNodeId) ?? null);
	const selectedEdge = $derived(edges.find((e) => e.id === selectedEdgeId) ?? null);

	// Conditional-branch cards for the Inspector when a condition node is
	// selected: the node's own branches (minus the default), in evaluation
	// order, each carrying its wired state and a display placeholder. Edits bind
	// straight to the branch objects on the node domain.
	const selectedConditionBranches = $derived.by(() => {
		const domain: any = selectedNode?.data?.domain;
		if (!domain || domain.type !== 'condition') return [];
		const wired = wiredBranchIds();
		return sortedBranches(domain)
			.filter((branch) => !branch.is_default)
			.map((branch, index) => ({
				branch,
				wired: wired.has(branch.id),
				placeholder: conditionSummary(branch) || m.branchDefaultName({ number: index + 1 })
			}));
	});

	// The selected condition node's default (otherwise) branch — always present
	// (exactly one is_default) — plus its wired state.
	const selectedConditionDefault = $derived.by((): { branch: any; wired: boolean } | null => {
		const domain: any = selectedNode?.data?.domain;
		if (!domain || domain.type !== 'condition') return null;
		const branch = (domain.branches ?? []).find((b: any) => b.is_default);
		return branch ? { branch, wired: wiredBranchIds().has(branch.id) } : null;
	});

	// ---------- save machinery ----------

	let saveState = $state<'idle' | 'dirty' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state<string | null>(null);
	let saveTimer: ReturnType<typeof setTimeout> | null = null;
	let validationErrors = $state<any[]>([]);
	let publishing = $state(false);

	function markDirty() {
		if (readonly) return;
		if (!restoring) {
			const now = Date.now();
			if (now - lastPushAt >= COALESCE_MS) {
				// Bursts (typing) coalesce into a single undo step.
				undoStack.push(lastSnapshot);
				if (undoStack.length > HISTORY_LIMIT) undoStack.shift();
				lastPushAt = now;
				redoStack = [];
				syncHistorySizes();
			}
			lastSnapshot = takeSnapshot(); // always track current state
		}
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

	// Node selected → the data browser needs it; data panel open → it shows
	// per-variable reference values.
	$effect(() => {
		if ((selectedNodeId || dataOpen) && !readonly) ensureReferenceRun();
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

	type RunState = 'visited' | 'active' | 'error' | 'warning';
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
		// Completed-with-item-errors (for_each, continue policy) reads amber —
		// distinct from red, which means the run stopped there.
		for (const entry of logs) {
			if (
				entry.event_type === 'action_executed' &&
				entry.node?.id &&
				Array.isArray(entry.data?.errors) &&
				entry.data.errors.length
			) {
				runView.nodeStates[entry.node.id] = 'warning';
			}
		}
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
				...visualData(n.data.domain, (n.data.error as string | null) ?? null),
				runState: n.data.runState ?? null
			}
		}));
		edges = edges.map((e) => ({ ...e, label: edgeLabel(e.data!.domain) || undefined }));
	}

	function serializeGraph() {
		return {
			// A condition node's `branches` (the source of truth for its routing)
			// ride along on the domain as-is.
			nodes: nodes.map((n) => ({
				...(n.data.domain as object),
				position: { x: Math.round(n.position.x), y: Math.round(n.position.y) }
			})),
			// Edges carry source_branch (the branch they wire) and never conditions.
			edges: edges.map((e) => {
				const { condition_groups: _drop, ...domain } = e.data!.domain as any;
				return {
					...domain,
					source: e.source,
					target: e.target,
					source_branch: domain.source_branch ?? null
				};
			}),
			variables
		};
	}

	// Single-flight: exactly one save on the wire at a time. Wholesale graph
	// PUTs landing out of order would silently revert newer state, so a save
	// requested mid-flight doesn't send a second racing request — it coalesces
	// into ONE trailing save that captures the latest canvas state after the
	// current one lands. Callers awaiting save() therefore always resolve
	// against a persistence of the state as of their call (or newer).
	let saveInFlight: Promise<boolean> | null = null;
	let saveQueued: Promise<boolean> | null = null;

	function save(): Promise<boolean> {
		if (!saveInFlight) {
			saveInFlight = doSave()
				.catch((error) => {
					saveError = String(error);
					saveState = 'error';
					return false;
				})
				.finally(() => {
					saveInFlight = null;
				});
			return saveInFlight;
		}
		if (!saveQueued) {
			saveQueued = saveInFlight
				.catch(() => false)
				.then(() => {
					saveQueued = null;
					return save();
				});
		}
		return saveQueued;
	}

	async function doSave(): Promise<boolean> {
		if (readonly || versionGone) return true;
		if (saveTimer) clearTimeout(saveTimer);
		saveState = 'saving';
		if (status === 'published' && !(await ensureDraft())) return false;
		const res = await fetch(opsUrl('save-graph'), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ version: activeVersionId, graph: serializeGraph() })
		});
		if (res.status === 404) {
			// The version vanished under us (discarded in another tab, or a
			// discard race): nothing here is savable anymore — resync to
			// reality instead of parking on an error the user can't act on.
			versionGone = true;
			saveError = m.draftNoLongerExists();
			saveState = 'error';
			await invalidateAll();
			return false;
		}
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

	let discarding = $state(false);

	function confirmDiscardDraft() {
		modalStore.trigger({
			type: 'confirm',
			title: m.discardWorkflowDraft(),
			body: m.discardWorkflowDraftConfirm(),
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				await discardDraft();
			}
		});
	}

	// Set the moment the backend confirms the draft is gone (or turns out to be
	// already gone): every save path checks it, so no race — in-flight autosave,
	// a keystroke during the page reload, a second discard click — can fire
	// requests at a deleted version.
	let versionGone = $state(false);

	async function discardDraft() {
		discarding = true;
		try {
			const res = await fetch(opsUrl('discard-draft'), {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ version: activeVersionId })
			});
			// 404 = the draft was already deleted (another tab, an earlier
			// half-finished discard): the goal state is reached either way,
			// so resync instead of surfacing the raw error.
			if (res.ok || res.status === 404) {
				versionGone = true;
				if (saveTimer) clearTimeout(saveTimer);
				await invalidateAll();
				// Force the remount: when this draft was auto-drafted in-session,
				// page data (still the published version) is unchanged by the
				// reload, so the page's {#key} alone would never fire.
				onDiscarded?.();
				// Deliberately leave `discarding` true: this instance is about to
				// be torn down; until then the button stays dead.
				return;
			}
			const body = await res.json().catch(() => ({}));
			saveError = body.error ?? body.detail ?? res.statusText;
			saveState = 'error';
			discarding = false;
		} catch (error) {
			saveError = String(error);
			saveState = 'error';
			discarding = false;
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
			if (body.error === 'draftAlreadyExists' && body.draft_id) {
				// Another tab (or an earlier half-finished attempt) already created
				// the draft: adopt it instead of erroring. The canvas keeps ITS
				// state as the source of truth — the next save wholesale-replaces
				// the adopted draft's content. Re-id first: our rows still carry
				// the PUBLISHED version's ids, and saving those into the draft
				// would hijack the published rows' primary keys.
				remapGraphIds();
				activeVersionId = body.draft_id;
				status = 'draft';
				if (body.draft_version_number) versionNumber = body.draft_version_number;
				return true;
			}
			saveError = body.error ?? res.statusText;
			saveState = 'error';
			return false;
		}
		const draft = await res.json();
		// The server clone has fresh row ids; the canvas keeps ITS state as the
		// source of truth (the next save wholesale-replaces the clone), so re-id
		// everything locally to avoid colliding with the published rows. Undo
		// history is remapped through the same id map, so ⌘Z can walk back
		// across the auto-draft boundary to the pre-edit (published) content.
		remapGraphIds();
		activeVersionId = draft.id;
		status = 'draft';
		versionNumber = draft.version_number;
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
		// Nodes first: this seeds the id map with fresh branch ids so the edges'
		// source_branch (processed next) resolves to the same new branch ids.
		nodes = nodes.map((n) => {
			const domain: any = { ...(n.data.domain as any), id: fresh(n.id) };
			if (Array.isArray(domain.branches)) {
				domain.branches = domain.branches.map((branch: any) => ({
					...branch,
					id: fresh(branch.id),
					condition_groups: (branch.condition_groups ?? []).map(remapGroup)
				}));
			}
			return { ...n, id: domain.id, data: { ...n.data, domain } };
		});
		edges = edges.map((e) => {
			const domain: any = { ...(e.data!.domain as any) };
			domain.id = fresh(e.id);
			domain.source = fresh(e.source);
			domain.target = fresh(e.target);
			// The wired branch's id was already re-mapped during the node pass.
			domain.source_branch = domain.source_branch ? fresh(domain.source_branch) : null;
			return {
				...e,
				id: domain.id,
				source: domain.source,
				target: domain.target,
				sourceHandle: domain.source_branch ?? undefined,
				data: { ...e.data, domain }
			};
		});
		if (selectedNodeId) selectedNodeId = idMap.get(selectedNodeId) ?? null;
		if (selectedEdgeId) selectedEdgeId = idMap.get(selectedEdgeId) ?? null;
		// Rebuild node visuals so data.branches carries the REMAPPED branch ids:
		// the condition node renders its handle DOM from data.branches, and the
		// edges now reference the new ids via sourceHandle — leaving the old ids
		// in place makes every condition edge unresolvable (silently dropped)
		// until something else happens to refresh visuals.
		refreshVisuals();

		// Undo snapshots hold pre-remap ids; restoring them verbatim into a
		// draft save would collide with the published rows' PKs. Walk every
		// snapshot through the SAME id map instead of wiping history — fresh()
		// memoizes, so ids of rows deleted before the remap (present only in
		// old snapshots) still map to stable new ids across all docs.
		const remapDoc = (doc: Doc): Doc => ({
			variables: doc.variables.map((v: any) => ({ ...v, id: fresh(v.id) })),
			nodes: doc.nodes.map((n: any) => ({
				...n,
				id: fresh(n.id),
				branches: Array.isArray(n.branches)
					? n.branches.map((branch: any) => ({
							...branch,
							id: fresh(branch.id),
							condition_groups: (branch.condition_groups ?? []).map(remapGroup)
						}))
					: n.branches
			})),
			edges: doc.edges.map((e: any) => ({
				...e,
				id: fresh(e.id),
				source: fresh(e.source),
				target: fresh(e.target),
				source_branch: e.source_branch ? fresh(e.source_branch) : null
			}))
		});
		undoStack = undoStack.map(remapDoc);
		redoStack = redoStack.map(remapDoc);
		if (lastSnapshot) lastSnapshot = remapDoc(lastSnapshot);
	}

	let runsOpen = $state(false);
	let runsPanel = $state<RunsPanel | null>(null);
	let triggersOpen = $state(false);
	let dataOpen = $state(false);
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
			// A fresh condition node starts with just the guaranteed default
			// (otherwise) branch; an if/else emerges once a conditional branch is
			// added. Branches are the node's source of truth for routing.
			...(type === 'condition'
				? {
						branches: [
							{
								id: crypto.randomUUID(),
								name: '',
								order: 0,
								is_default: true,
								condition_groups: []
							}
						]
					}
				: {}),
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

	function isValidConnection(connection: Connection | Edge): boolean {
		if (connection.source === connection.target) return false;
		const source = nodes.find((n) => n.id === connection.source);
		const target = nodes.find((n) => n.id === connection.target);
		if (!source || !target) return false;
		if (source.data.nodeType === 'end' || target.data.nodeType === 'trigger') return false;
		// A condition-node port IS a branch: at most one wire per branch.
		const sourceBranch = connection.sourceHandle ?? null;
		if (sourceBranch && edges.some((e) => (e.data?.domain as any)?.source_branch === sourceBranch))
			return false;
		// No duplicate wire for the same (source, target, branch); different
		// branches of a condition node may legitimately point at the same target.
		if (
			edges.some(
				(e) =>
					e.source === connection.source &&
					e.target === connection.target &&
					((e.data?.domain as any)?.source_branch ?? null) === sourceBranch
			)
		)
			return false;
		return true;
	}

	function handleConnect(connection: Connection) {
		// The source handle id on a condition node IS the branch id being wired;
		// plain nodes have no handle id, so source_branch stays null.
		const sourceBranch = connection.sourceHandle ?? null;
		const outgoing = edges.filter((e) => e.source === connection.source);

		const domain = {
			id: crypto.randomUUID(),
			source: connection.source,
			target: connection.target,
			source_branch: sourceBranch,
			label: '',
			priority: outgoing.length
		};
		// SvelteFlow already appended a default edge for this connection; replace
		// it with ours so the id is the persisted client UUID.
		edges = edges.map((e) =>
			e.source === connection.source && e.target === connection.target && !e.data?.domain
				? toFlowEdge(domain)
				: e
		);
		if (sourceBranch) {
			// Wiring a branch: select the condition node so the Inspector shows its
			// branch list, and rebuild visuals so the branch flips to "wired".
			selectedNodeId = connection.source;
			selectedEdgeId = null;
			refreshVisuals();
		} else {
			selectedEdgeId = domain.id;
			selectedNodeId = null;
		}
		markDirty();
	}

	function deleteNode(id: string) {
		nodes = nodes.filter((n) => n.id !== id);
		edges = edges.filter((e) => e.source !== id && e.target !== id);
		if (selectedNodeId === id) selectedNodeId = null;
		refreshVisuals();
		markDirty();
	}

	// ---------- condition-node branch edits (branches are node data) ----------

	function conditionNodeDomain(nodeId: string): any | null {
		const domain: any = nodes.find((n) => n.id === nodeId)?.data?.domain;
		return domain?.type === 'condition' ? domain : null;
	}

	function addBranch(nodeId: string) {
		const domain = conditionNodeDomain(nodeId);
		if (!domain) return;
		const order = (domain.branches ?? []).filter((b: any) => !b.is_default).length;
		domain.branches = [
			...(domain.branches ?? []),
			{
				id: crypto.randomUUID(),
				name: '',
				order,
				is_default: false,
				condition_groups: [
					{
						operator: 'and',
						order: 0,
						conditions: [{ variable: variables[0]?.id ?? '', op: 'eq', value: '', order: 0 }],
						children: []
					}
				]
			}
		];
		selectedNodeId = nodeId;
		selectedEdgeId = null;
		refreshVisuals();
		markDirty();
	}

	function deleteBranch(nodeId: string, branchId: string) {
		const domain = conditionNodeDomain(nodeId);
		if (!domain) return;
		domain.branches = (domain.branches ?? []).filter((b: any) => b.id !== branchId);
		// Renumber the surviving conditional branches to stay 0..n-1.
		domain.branches
			.filter((b: any) => !b.is_default)
			.sort((a: any, b: any) => (a.order ?? 0) - (b.order ?? 0))
			.forEach((b: any, index: number) => (b.order = index));
		// A wired branch drops its edge; the default keeps its guaranteed slot.
		edges = edges.filter((e) => (e.data?.domain as any)?.source_branch !== branchId);
		refreshVisuals();
		markDirty();
	}

	// Swap two conditional branches by order (index within the conditional list,
	// default excluded — it is pinned last by is_default, not by order value).
	function moveBranch(nodeId: string, index: number, delta: number) {
		const domain = conditionNodeDomain(nodeId);
		if (!domain) return;
		const conditional = (domain.branches ?? [])
			.filter((b: any) => !b.is_default)
			.sort((a: any, b: any) => (a.order ?? 0) - (b.order ?? 0));
		const target = index + delta;
		if (target < 0 || target >= conditional.length) return;
		conditional.forEach((b: any, i: number) => (b.order = i));
		conditional[index].order = target;
		conditional[target].order = index;
		refreshVisuals();
		markDirty();
	}

	// Returns the created variable's id — or the existing one's on a duplicate
	// key — so inline creators can select it right away.
	function addVariable(key: string, type: string): string | null {
		const existing = variables.find((v) => v.key === key);
		if (existing) return existing.id;
		const id = crypto.randomUUID();
		variables = [...variables, { id, key, type, default_value: null }];
		markDirty();
		return id;
	}

	function removeVariable(id: string) {
		variables = variables.filter((v) => v.id !== id);
		// Strip branch conditions that referenced it so the save doesn't 400.
		for (const node of nodes) {
			const domain: any = node.data?.domain;
			if (domain?.type !== 'condition') continue;
			for (const branch of domain.branches ?? []) {
				for (const group of branch.condition_groups ?? []) {
					group.conditions = (group.conditions ?? []).filter((c: any) => c.variable !== id);
				}
			}
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

	// The Workflow panel (Inspector, no selection) lists secret names even in
	// readonly views; values never leave the backend either way.
	$effect(() => {
		refreshSecrets();
	});

	$effect(() => {
		refreshRegistrations();
	});

	setContext('workflowEditor', {
		get readonly() {
			return readonly;
		},
		deleteNode,
		addBranch
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

<div class="flex flex-col h-full gap-3">
	<div class="flex items-center gap-3 shrink-0">
		<h1 class="text-lg font-semibold text-surface-900-100">{workflowName}</h1>
		<span class="badge {badge.class} text-xs" data-testid="version-badge">
			v{versionNumber} · {badge.label()}
		</span>
		{#if workflowDescription}
			<p class="text-sm text-surface-600-400 truncate">{workflowDescription}</p>
		{/if}
		<div class="ml-auto flex items-center justify-end gap-2 shrink-0">
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
						data-testid="save-error"
						title={saveError}
						onclick={save}
					>
						<i class="fa-solid fa-triangle-exclamation"></i>
						{saveError}
					</button>
				{/if}
			{/if}
			{#if !readonly}
				<button
					type="button"
					class="btn-icon preset-tonal text-sm"
					title={m.undo()}
					aria-label={m.undo()}
					disabled={!historySizes.undo}
					onclick={undo}
					data-testid="undo-graph"
				>
					<i class="fa-solid fa-rotate-left"></i>
				</button>
				<button
					type="button"
					class="btn-icon preset-tonal text-sm"
					title={m.redo()}
					aria-label={m.redo()}
					disabled={!historySizes.redo}
					onclick={redo}
					data-testid="redo-graph"
				>
					<i class="fa-solid fa-rotate-right"></i>
				</button>
			{/if}
			<a
				href={`/workflows/${workflowId}/export-yaml`}
				class="btn preset-tonal text-sm"
				title={m.exportWorkflowYaml()}
				aria-label={m.exportWorkflowYaml()}
				data-testid="export-workflow-yaml"
			>
				<i class="fa-solid fa-download"></i> Export
			</a>
			{#if !readonly && status === 'draft' && hasPublishedFallback}
				<button
					type="button"
					class="btn preset-tonal text-sm text-error-500"
					disabled={discarding || saveState === 'saving'}
					onclick={confirmDiscardDraft}
					data-testid="discard-draft"
				>
					{#if discarding}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{:else}
						<i class="fa-solid fa-trash-can mr-1"></i>
					{/if}
					{m.discardWorkflowDraft()}
				</button>
			{/if}
			{#if !readonly && status === 'draft'}
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
		</div>
	</div>

	<div
		class="flex-1 min-h-0 flex bg-surface-50-950 rounded-base overflow-hidden border border-surface-200-800"
	>
		{#if !readonly}
			<Palette onAdd={addNode} />
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
					ondelete={readonly
						? undefined
						: () => {
								// Deleted edges may have been condition branches: collapse rows.
								refreshVisuals();
								markDirty();
							}}
					onnodeclick={({ node }) => {
						selectedNodeId = node.id;
						selectedEdgeId = null;
					}}
					onedgeclick={({ edge }) => {
						// Condition branches are edited on their switch block, not per edge.
						if (isConditionNodeId(edge.source)) {
							selectedNodeId = edge.source;
							selectedEdgeId = null;
						} else {
							selectedEdgeId = edge.id;
							selectedNodeId = null;
						}
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
					<Controls showLock={false}>
						{#if !readonly}
							<ControlButton
								onclick={tidyUp}
								title={m.tidyUp()}
								aria-label={m.tidyUp()}
								data-testid="tidy-up"
							>
								<i class="fa-solid fa-wand-magic-sparkles"></i>
							</ControlButton>
						{/if}
					</Controls>
					<MiniMap />

					<Panel position="top-left">
						<div class="flex items-center gap-2">
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
							<button
								type="button"
								class="btn preset-tonal text-sm"
								class:preset-filled-secondary-500={dataOpen}
								onclick={() => (dataOpen = !dataOpen)}
								data-testid="toggle-data"
							>
								<i class="fa-solid fa-cube mr-1"></i>
								{m.workflowVariables()}
							</button>
						</div>
					</Panel>
					<Panel position="top-right">
						<div class="flex items-center gap-2">
							<div class="relative">
								<button
									type="button"
									class="btn preset-filled-primary-500 text-sm"
									disabled={running}
									onclick={runWorkflow}
									data-testid="run-workflow"
								>
									{#if running}
										<i class="fa-solid fa-spinner fa-spin mr-1"></i>
									{:else}
										<i class="fa-solid fa-play mr-1"></i>
									{/if}
									{m.executeWorkflow()}
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

			{#if dataOpen}
				<aside
					class="h-60 shrink-0 border-t border-surface-200-800 bg-surface-100-900 overflow-y-auto"
					data-testid="data-panel"
				>
					<div class="p-3 max-w-3xl">
						<WorkflowDataPanel
							{variables}
							{secrets}
							{referenceVariables}
							{readonly}
							columns
							onAddVariable={addVariable}
							onRemoveVariable={removeVariable}
							onAddSecret={addSecret}
							onRemoveSecret={removeSecret}
						/>
					</div>
				</aside>
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

		<!-- No selection → no panel: the canvas takes the full width, and
		     workflow-scoped data lives in the Variables toggle instead. -->
		{#if !readonly && (selectedNode || selectedEdge)}
			<Inspector
				{selectedNode}
				{selectedEdge}
				branches={selectedConditionBranches}
				defaultBranch={selectedConditionDefault}
				onAddBranch={() => selectedNode && addBranch(selectedNode.id)}
				onDeleteBranch={(branchId) => selectedNode && deleteBranch(selectedNode.id, branchId)}
				onMoveBranch={(index, delta) => selectedNode && moveBranch(selectedNode.id, index, delta)}
				{readonly}
				{variables}
				{secrets}
				onAddVariable={addVariable}
				onAddSecret={addSecret}
				{taskTemplates}
				{subprocessCandidates}
				{creatableModels}
				{readableModels}
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
		{/if}
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
