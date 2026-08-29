<script lang="ts" module>
	// The event catalog is instance-wide and static: fetch it once per page
	// load, shared across Inspector instances.
	interface EventKey {
		key: string;
		model: string;
		action: string;
	}
	let eventKeysCache: EventKey[] | null = null;
</script>

<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { fetchHookSecret, publicHookUrl } from './hook-url';
	import { postOps } from './ops';
	import DataBrowser from './DataBrowser.svelte';
	import { dig, renderTemplate } from './expressions';
	import { TRIGGER_ICONS } from './nodes/TriggerNode.svelte';
	import {
		newCondition,
		treeToGroups,
		groupsToTree,
		FILTER_OPS,
		type Condition
	} from './filter-dnf';
	import { VARIABLE_TYPES } from './builder-constants';

	interface Option {
		id: string;
		name?: string;
		str?: string;
		code?: string;
	}

	interface Props {
		selectedNode: any | null;
		selectedEdge: any | null;
		// Conditional-branch cards for a selected condition node: the node's own
		// branches (default excluded), in evaluation order. Edits bind straight to
		// the branch objects on the node domain.
		branches?: { branch: any; wired: boolean; placeholder: string }[];
		// The guaranteed default (otherwise) branch and its wired state; always
		// present for a condition node (exactly one is_default).
		defaultBranch?: { branch: any; wired: boolean } | null;
		onAddBranch?: () => void;
		onDeleteBranch?: (branchId: string) => void;
		onMoveBranch?: (index: number, delta: number) => void;
		readonly?: boolean;
		variables: { id: string; key: string; type: string }[];
		secrets?: { id: string; name: string }[];
		// Creates the variable (or finds the existing one on a duplicate key)
		// and returns its id, so inline creators can select it right away.
		onAddVariable?: (key: string, type: string) => string | null;
		onAddSecret?: (name: string, value: string) => void;
		taskTemplates: Option[];
		subprocessCandidates: Option[];
		creatableModels?: any[];
		updatableModels?: any[];
		readableModels?: { key: string; fields: string[] }[];
		fkOptions?: Record<string, Option[]>;
		workflowId: string;
		registrationsByRef?: Record<string, any>;
		onRegistrationsChanged?: () => void;
		referenceRunId?: string | null;
		referenceVariables?: Record<string, unknown>;
		referenceNodes?: { key: string; label: string; output: unknown }[];
		// Static upstream summaries for the loop collection picker — available
		// even without a reference run.
		upstreamNodes?: { ref: string; label: string; actionConfig: any; isLoop?: boolean }[];
		secretNames?: string[];
		onChange: () => void;
	}

	let {
		selectedNode = $bindable(),
		selectedEdge = $bindable(),
		branches = [],
		defaultBranch = null,
		onAddBranch,
		onDeleteBranch,
		onMoveBranch,
		readonly = false,
		variables,
		secrets = [],
		onAddVariable,
		onAddSecret,
		taskTemplates,
		subprocessCandidates,
		creatableModels = [],
		updatableModels = [],
		readableModels = [],
		fkOptions = {},
		workflowId,
		registrationsByRef = {},
		onRegistrationsChanged,
		referenceRunId = null,
		referenceVariables = {},
		referenceNodes = [],
		upstreamNodes = [],
		secretNames = [],
		onChange
	}: Props = $props();

	// ---------- expression assist ----------

	let lastFocusedInput: HTMLInputElement | HTMLTextAreaElement | null = null;
	let lastFocusedValue = $state('');

	function isTemplateField(el: EventTarget | null): el is HTMLInputElement | HTMLTextAreaElement {
		return (
			(el instanceof HTMLInputElement && el.type === 'text') || el instanceof HTMLTextAreaElement
		);
	}

	function trackFocus(event: Event) {
		if (isTemplateField(event.target) && !event.target.readOnly) {
			lastFocusedInput = event.target;
			lastFocusedValue = event.target.value;
		}
	}

	function trackInput(event: Event) {
		if (event.target === lastFocusedInput && isTemplateField(event.target)) {
			lastFocusedValue = event.target.value;
		}
	}

	let copiedExpression = $state(false);
	function insertExpression(expression: string) {
		const el = lastFocusedInput;
		if (el && document.contains(el)) {
			const start = el.selectionStart ?? el.value.length;
			const end = el.selectionEnd ?? start;
			el.value = el.value.slice(0, start) + expression + el.value.slice(end);
			el.dispatchEvent(new Event('input', { bubbles: true }));
			el.focus();
			el.setSelectionRange(start + expression.length, start + expression.length);
			lastFocusedValue = el.value;
		} else {
			navigator.clipboard.writeText(expression);
			copiedExpression = true;
			setTimeout(() => (copiedExpression = false), 1200);
		}
	}

	const previewContext = $derived({
		...referenceVariables,
		nodes: Object.fromEntries(referenceNodes.map((n) => [n.key, n.output])),
		secrets: Object.fromEntries(secretNames.map((name) => [name, '•••']))
	});
	const livePreview = $derived(
		lastFocusedValue.includes('{{') ? renderTemplate(lastFocusedValue, previewContext) : null
	);

	// emit_event is hidden pending the event-node redesign (correlation +
	// buffering); the engine still executes it for graphs that carry it.
	const ACTION_TYPES = [
		'create_object',
		'update_object',
		'read_objects',
		'http_request',
		'send_email',
		'provision_folder',
		'provision_user',
		'manage_group_membership',
		'set_variables',
		'date_offset',
		'log'
	];

	const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];

	const BUILTIN_GROUPS = [
		{ code: 'BI-UG-AUD', label: 'reader' },
		{ code: 'BI-UG-APP', label: 'approver' },
		{ code: 'BI-UG-ANA', label: 'analyst' },
		{ code: 'BI-UG-DMA', label: 'domainManager' },
		{ code: 'BI-UG-ADE', label: 'auditee' }
	];

	const nodeDomain = $derived(selectedNode?.data?.domain);
	const edgeDomain = $derived(selectedEdge?.data?.domain);
	const actionConfig = $derived(nodeDomain?.action_config);

	const ACTION_CONFIG_DEFAULTS: Record<string, object> = {
		log: { message: '' },
		set_variables: { variables: {} },
		date_offset: { base: '', days: 30, weeks: 0, output: '' },
		create_object: { model: 'applied_control', fields: { name: '' }, upsert: false },
		update_object: { model: 'applied_control', id: '', fields: {}, m2m: {} },
		read_objects: {
			model: 'applied_control',
			mode: 'list',
			filters: {},
			order_by: '-created_at',
			limit: 25
		},
		http_request: { method: 'GET', url: '', headers: {}, body: '', timeout: 15 },
		send_email: { recipients: '', subject: '', body: '' },
		provision_folder: { name: '', parent: '', create_default_groups: true },
		provision_user: {
			email: '',
			first_name: '',
			last_name: '',
			is_active: true,
			send_onboarding_email: false
		},
		manage_group_membership: {
			user: '',
			folder: '',
			builtin_group: 'BI-UG-ANA',
			operation: 'add'
		},
		emit_event: { event_key: '' }
	};

	const creatableEntry = $derived(
		creatableModels.find((entry) => entry.key === actionConfig?.model)
	);
	const readableEntry = $derived(readableModels.find((entry) => entry.key === actionConfig?.model));
	const updatableEntry = $derived(
		updatableModels.find((entry) => entry.key === actionConfig?.model)
	);

	function resetUpdateFields() {
		// Field and relation names are per-model.
		actionConfig.fields = {};
		actionConfig.m2m = {};
		onChange();
	}

	// Added explicitly, never pre-seeded: a row with no ids fails publish.
	const unusedRelations = $derived(
		Object.keys(updatableEntry?.m2m_fields ?? {}).filter(
			(name) => !(name in (actionConfig?.m2m ?? {}))
		)
	);

	function addRelationRow() {
		const name = unusedRelations[0];
		if (!name) return;
		actionConfig.m2m = { ...actionConfig.m2m, [name]: { op: 'add', values: '' } };
		onChange();
	}

	function removeRelationRow(name: string) {
		const { [name]: _dropped, ...rest } = actionConfig.m2m ?? {};
		actionConfig.m2m = rest;
		onChange();
	}

	function renameRelationRow(previous: string, next: string) {
		if (previous === next) return;
		const spec = actionConfig.m2m?.[previous] ?? { op: 'add', values: '' };
		const { [previous]: _dropped, ...rest } = actionConfig.m2m ?? {};
		actionConfig.m2m = { ...rest, [next]: spec };
		onChange();
	}

	function resetCreateFields() {
		actionConfig.fields = { name: actionConfig.fields?.name ?? '' };
		onChange();
	}

	function initActionConfig() {
		const type = actionConfig.type;
		const defaults: any = ACTION_CONFIG_DEFAULTS[type] ?? {};
		for (const [key, value] of Object.entries(defaults)) {
			// Clone: the nested literals are shared, and bindings mutate them in
			// place, so two nodes of the same type would edit one object.
			if (actionConfig[key] === undefined) actionConfig[key] = structuredClone(value);
		}
		onChange();
	}

	// Older nodes may carry a bare {type} config; make sure the shape the
	// bindings expect exists before the template reads it.
	$effect(() => {
		if (nodeDomain?.type === 'action' && actionConfig?.type) {
			const defaults: any = ACTION_CONFIG_DEFAULTS[actionConfig.type] ?? {};
			for (const [key, value] of Object.entries(defaults)) {
				if (actionConfig[key] === undefined) actionConfig[key] = value;
			}
		}
		if (nodeDomain?.type === 'trigger') {
			nodeDomain.trigger_config ??= { type: 'manual' };
			nodeDomain.input_mapping ??= {};
		}
		if (nodeDomain?.type === 'loop') {
			nodeDomain.loop_config ??= { collection: '', on_item_error: 'continue' };
			nodeDomain.loop_config.collect ??= '';
		}
		if (['action', 'subprocess', 'loop'].includes(nodeDomain?.type) && !nodeDomain.output_mapping) {
			nodeDomain.output_mapping = {};
		}
	});

	// What a path into this step's output typically looks like, for the hint.
	const OUTPUT_EXAMPLES: Record<string, string> = {
		http_request: 'body.summary',
		create_object: 'created_object_id',
		update_object: 'object_id',
		read_objects: 'results.0.name',
		provision_folder: 'folder_id',
		provision_user: 'user_id',
		manage_group_membership: 'group_id',
		send_email: 'subject',
		date_offset: 'result',
		log: 'message'
	};
	const outputExample = $derived(
		nodeDomain?.type === 'subprocess'
			? 'a child workflow variable key'
			: nodeDomain?.type === 'loop'
				? 'count'
				: (OUTPUT_EXAMPLES[actionConfig?.type] ?? 'created_object_id')
	);

	// ---------- trigger nodes ----------

	const TRIGGER_LABELS: Record<string, () => string> = {
		manual: m.triggerManual,
		webhook: m.triggerWebhook,
		schedule: m.triggerSchedule,
		internal_event: m.triggerInternalEvent
	};

	const triggerConfig = $derived(nodeDomain?.type === 'trigger' ? nodeDomain.trigger_config : null);
	const triggerRegistration = $derived(
		nodeDomain?.type === 'trigger' && nodeDomain.ref
			? (registrationsByRef[nodeDomain.ref] ?? null)
			: null
	);
	// The URL credential is change-gated server-side and fetched on demand;
	// viewers get null and the hook URL block stays hidden.
	let hookSecrets = $state<Record<string, string>>({});
	$effect(() => {
		const registration = triggerRegistration;
		if (!registration || triggerConfig?.type !== 'webhook') return;
		if (registration.id in hookSecrets) return;
		fetchHookSecret(workflowId, registration.id).then((secret) => {
			if (secret) hookSecrets[registration.id] = secret;
		});
	});
	const nodeHookUrl = $derived(
		triggerRegistration && triggerConfig?.type === 'webhook' && hookSecrets[triggerRegistration.id]
			? publicHookUrl(workflowId, nodeDomain.ref, hookSecrets[triggerRegistration.id])
			: null
	);

	const triggerOps = (action: string, body: Record<string, unknown>) =>
		postOps(workflowId, action, body);

	let copiedHook = $state(false);
	async function copyHookUrl() {
		if (!nodeHookUrl) return;
		await navigator.clipboard.writeText(nodeHookUrl);
		copiedHook = true;
		setTimeout(() => (copiedHook = false), 1500);
	}

	async function rotateSecret() {
		if (!triggerRegistration) return;
		const res = await triggerOps('rotate-trigger-secret', { id: triggerRegistration.id });
		if (res.ok) {
			const body = await res.json().catch(() => ({}));
			if (typeof body.secret === 'string') hookSecrets[triggerRegistration.id] = body.secret;
			onRegistrationsChanged?.();
		}
	}

	// Event catalog, fetched lazily the first time an internal_event trigger
	// node is selected.
	let eventKeys = $state<EventKey[]>(eventKeysCache ?? []);
	let eventKeysFetchInFlight = false;
	async function loadEventKeys() {
		if (eventKeysCache) {
			eventKeys = eventKeysCache;
			return;
		}
		if (eventKeysFetchInFlight) return;
		eventKeysFetchInFlight = true;
		try {
			const res = await triggerOps('event-keys', {});
			if (!res.ok) return;
			const data = await res.json().catch(() => null);
			eventKeysCache = Array.isArray(data) ? data : (data?.results ?? []);
			eventKeys = eventKeysCache ?? [];
		} finally {
			eventKeysFetchInFlight = false;
		}
	}

	$effect(() => {
		if (triggerConfig?.type === 'internal_event') loadEventKeys();
	});

	const eventKeysByModel = $derived.by(() => {
		const map = new Map<string, EventKey[]>();
		for (const ek of eventKeys) {
			if (!map.has(ek.model)) map.set(ek.model, []);
			map.get(ek.model)!.push(ek);
		}
		return [...map.entries()];
	});

	// ---------- internal_event DNF filter builder ----------

	const FIELD_CHIPS = ['status', 'folder', 'filtering_labels'];
	const CHANGED_HELP =
		'Match the transition (field just changed to this value), not the standing state.';

	// The builder edits an entries structure and writes the whole tree back on
	// every change; rebuilt when the selected node changes (same pattern as
	// headerEntries above).
	let filterGroups = $state<Condition[][]>([]);
	let filterRawMode = $state(false);
	let filterRawJson = $state('{}');
	let filterRawError = $state(false);
	let filterNodeId: string | null = null;
	$effect(() => {
		const nodeId =
			nodeDomain?.type === 'trigger' && triggerConfig?.type === 'internal_event'
				? selectedNode.id
				: null;
		if (nodeId !== filterNodeId) {
			filterNodeId = nodeId;
			filterRawError = false;
			if (!nodeId) {
				filterGroups = [];
				filterRawMode = false;
				filterRawJson = '{}';
				return;
			}
			const dnf = treeToGroups(triggerConfig.filters);
			if (dnf === null) {
				filterRawMode = true;
				filterRawJson = JSON.stringify(triggerConfig.filters ?? {}, null, 2);
				filterGroups = [];
			} else {
				filterRawMode = false;
				filterRawJson = '{}';
				filterGroups = dnf;
			}
		}
	});

	function syncFilters() {
		triggerConfig.filters = groupsToTree(filterGroups);
		onChange();
	}

	function syncRawFilters() {
		try {
			triggerConfig.filters = JSON.parse(filterRawJson);
			filterRawError = false;
			onChange();
		} catch {
			filterRawError = true;
		}
	}

	// read_objects filter builder — same DNF editor pattern as the
	// event-trigger filters above, keyed on the selected read node. Trees that
	// don't fit the DNF shape (e.g. "not" groups from an imported YAML) fall
	// back to raw JSON editing.
	let readFilterGroups = $state<Condition[][]>([]);
	let readFilterRawMode = $state(false);
	let readFilterRawJson = $state('{}');
	let readFilterRawError = $state(false);
	let readFilterNodeId: string | null = null;
	$effect(() => {
		const nodeId =
			nodeDomain?.type === 'action' && actionConfig?.type === 'read_objects'
				? selectedNode.id
				: null;
		if (nodeId !== readFilterNodeId) {
			readFilterNodeId = nodeId;
			readFilterRawError = false;
			if (!nodeId) {
				readFilterGroups = [];
				readFilterRawMode = false;
				readFilterRawJson = '{}';
				return;
			}
			const dnf = treeToGroups(actionConfig.filters);
			if (dnf === null) {
				readFilterRawMode = true;
				readFilterRawJson = JSON.stringify(actionConfig.filters ?? {}, null, 2);
				readFilterGroups = [];
			} else {
				readFilterRawMode = false;
				readFilterRawJson = '{}';
				readFilterGroups = dnf;
			}
		}
	});

	function syncReadFilters() {
		actionConfig.filters = groupsToTree(readFilterGroups);
		onChange();
	}

	function syncReadRawFilters() {
		try {
			actionConfig.filters = JSON.parse(readFilterRawJson);
			readFilterRawError = false;
			onChange();
		} catch {
			readFilterRawError = true;
		}
	}

	function resetReadModel() {
		// Field whitelists differ per model: stale filters/ordering would fail
		// publish validation.
		actionConfig.filters = {};
		actionConfig.order_by = '-created_at';
		readFilterGroups = [];
		readFilterRawMode = false;
		onChange();
	}

	const readOrderDesc = $derived(
		typeof actionConfig?.order_by === 'string' && actionConfig.order_by.startsWith('-')
	);
	const readOrderField = $derived(
		typeof actionConfig?.order_by === 'string'
			? actionConfig.order_by.replace(/^-/, '')
			: 'created_at'
	);
	function setReadOrder(field: string, descending: boolean) {
		actionConfig.order_by = (descending ? '-' : '') + field;
		onChange();
	}

	// Loop node: resolve the collection against the reference run
	// so the builder can preview the iteration count and offer {{item.*}} paths.
	const COLLECTION_RE = /^\{\{\s*([\w.]+)\s*\}\}$/;
	const loopConfig = $derived(nodeDomain?.type === 'loop' ? nodeDomain.loop_config : null);
	const referenceContext = $derived({
		...referenceVariables,
		nodes: Object.fromEntries(referenceNodes.map((n) => [n.key, n.output]))
	});
	const collectionPreview = $derived.by(() => {
		const expression = loopConfig?.collection;
		if (!expression || typeof expression !== 'string') return null;
		const match = expression.match(COLLECTION_RE);
		if (!match) return { invalid: true, count: 0, first: undefined };
		const resolved = dig(referenceContext, match[1]);
		if (resolved === undefined) return null; // no reference data — no verdict
		if (!Array.isArray(resolved)) return { invalid: true, count: 0, first: undefined };
		return { invalid: false, count: resolved.length, first: resolved[0] };
	});

	// Collection picker: enumerate candidate arrays instead of
	// making the user type an expression. Static candidates come from upstream
	// node shapes we know (list reads, per-item actions); dynamic ones from
	// whatever actually resolved to an array in the reference run.
	function collectArrayPaths(value: unknown, base: string, depth: number, out: any[]) {
		if (depth > 2 || value === null || typeof value !== 'object') return;
		for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
			const path = base ? `${base}.${key}` : key;
			if (Array.isArray(child)) {
				if (child.length) out.push({ path, count: child.length });
			} else {
				collectArrayPaths(child, path, depth + 1, out);
			}
		}
	}

	const collectionChoices = $derived.by(() => {
		const choices = new Map<string, { expr: string; label: string; count: number | null }>();
		for (const upstream of upstreamNodes) {
			const config = upstream.actionConfig ?? {};
			const isListRead = config.type === 'read_objects' && (config.mode ?? 'list') === 'list';
			if (isListRead || upstream.isLoop) {
				const expr = `{{nodes.${upstream.ref}.results}}`;
				choices.set(expr, { expr, label: `${upstream.label} → results`, count: null });
			}
		}
		for (const nodeData of referenceNodes) {
			const found: { path: string; count: number }[] = [];
			collectArrayPaths(nodeData.output, '', 0, found);
			for (const entry of found) {
				const expr = `{{nodes.${nodeData.key}.${entry.path}}}`;
				choices.set(expr, {
					expr,
					label: `${nodeData.label} → ${entry.path}`,
					count: entry.count
				});
			}
		}
		for (const [key, value] of Object.entries(referenceVariables)) {
			if (Array.isArray(value) && value.length) {
				choices.set(`{{${key}}}`, {
					expr: `{{${key}}}`,
					label: key,
					count: value.length
				});
			}
		}
		return [...choices.values()];
	});

	// Custom-expression escape hatch, keyed on the selected loop node: stored
	// expressions that aren't among the detected choices render as custom.
	let collectionIsCustom = $state(false);
	let collectionNodeId: string | null = null;
	$effect(() => {
		const nodeId = nodeDomain?.type === 'loop' ? selectedNode.id : null;
		if (nodeId !== collectionNodeId) {
			collectionNodeId = nodeId;
			collectionIsCustom =
				!!loopConfig?.collection &&
				!collectionChoices.some((c) => c.expr === loopConfig.collection);
		}
	});

	const itemChips = $derived.by(() => {
		const first =
			collectionPreview && !collectionPreview.invalid ? collectionPreview.first : undefined;
		if (first === null || typeof first !== 'object' || Array.isArray(first)) return [];
		return Object.keys(first as Record<string, unknown>).slice(0, 10);
	});

	function addInputMapping() {
		const used = new Set(Object.keys(nodeDomain.input_mapping ?? {}));
		const candidate = variables.find((v) => !used.has(v.key));
		if (!candidate) return;
		nodeDomain.input_mapping = { ...nodeDomain.input_mapping, [candidate.key]: '' };
		onChange();
	}

	function removeInputMapping(key: string) {
		const { [key]: _, ...rest } = nodeDomain.input_mapping;
		nodeDomain.input_mapping = rest;
		onChange();
	}

	function addOutputMapping() {
		const used = new Set(Object.keys(nodeDomain.output_mapping ?? {}));
		const candidate = variables.find((v) => !used.has(v.key));
		if (!candidate) return;
		nodeDomain.output_mapping = { ...nodeDomain.output_mapping, [candidate.key]: '' };
		onChange();
	}

	function removeOutputMapping(key: string) {
		const { [key]: _, ...rest } = nodeDomain.output_mapping;
		nodeDomain.output_mapping = rest;
		onChange();
	}

	// Mapping rows key on a variable; the row's select swaps which one while
	// keeping the entered path/value and the row's position.
	function renameMappingKey(
		map: Record<string, string>,
		oldKey: string,
		newKey: string
	): Record<string, string> {
		const out: Record<string, string> = {};
		for (const [k, v] of Object.entries(map)) out[k === oldKey ? newKey : k] = v;
		return out;
	}

	// Selectable targets for a mapping row: every declared variable not
	// already used by a sibling row, plus the row's current key (which may be
	// undeclared on imported graphs — it must stay visible).
	function mappingKeyOptions(map: Record<string, unknown> | undefined, current: string) {
		const used = new Set(Object.keys(map ?? {}));
		const keys = variables.map((v) => v.key).filter((k) => k === current || !used.has(k));
		if (!keys.includes(current)) keys.unshift(current);
		return keys;
	}

	function renameOutputMapping(oldKey: string, newKey: string) {
		if (!newKey || newKey === oldKey || (nodeDomain.output_mapping ?? {})[newKey] !== undefined)
			return;
		nodeDomain.output_mapping = renameMappingKey(nodeDomain.output_mapping, oldKey, newKey);
		onChange();
	}

	function renameInputMapping(oldKey: string, newKey: string) {
		if (!newKey || newKey === oldKey || (nodeDomain.input_mapping ?? {})[newKey] !== undefined)
			return;
		nodeDomain.input_mapping = renameMappingKey(nodeDomain.input_mapping, oldKey, newKey);
		onChange();
	}

	function renameSetVariableRow(oldKey: string, newKey: string) {
		if (!newKey || newKey === oldKey || (actionConfig.variables ?? {})[newKey] !== undefined)
			return;
		actionConfig.variables = renameMappingKey(actionConfig.variables, oldKey, newKey);
		onChange();
	}

	function addSetVariableRow() {
		const used = new Set(Object.keys(actionConfig.variables ?? {}));
		const candidate = variables.find((v) => !used.has(v.key));
		if (!candidate) return;
		actionConfig.variables = { ...actionConfig.variables, [candidate.key]: '' };
		onChange();
	}

	function removeSetVariableRow(key: string) {
		const { [key]: _, ...rest } = actionConfig.variables;
		actionConfig.variables = rest;
		onChange();
	}

	// HTTP headers are a plain dict in the config, but editing keys in place
	// would recreate the inputs on every keystroke. Edit an entries array
	// instead and write the whole dict back on every change.
	let headerEntries = $state<{ key: string; value: string }[]>([]);
	let headerEntriesNodeId: string | null = null;
	$effect(() => {
		const nodeId =
			nodeDomain?.type === 'action' && actionConfig?.type === 'http_request'
				? selectedNode.id
				: null;
		if (nodeId !== headerEntriesNodeId) {
			headerEntriesNodeId = nodeId;
			headerEntries = nodeId
				? Object.entries(actionConfig.headers ?? {}).map(([key, value]) => ({
						key,
						value: String(value)
					}))
				: [];
		}
	});

	function syncHeaders() {
		const headers: Record<string, string> = {};
		for (const entry of headerEntries) {
			if (entry.key.trim()) headers[entry.key.trim()] = entry.value;
		}
		actionConfig.headers = headers;
		onChange();
	}

	function addHeaderRow() {
		headerEntries = [...headerEntries, { key: '', value: '' }];
	}

	function removeHeaderRow(index: number) {
		headerEntries = headerEntries.filter((_, i) => i !== index);
		syncHeaders();
	}

	function optionLabel(option: Option): string {
		return option.name ?? option.str ?? option.id;
	}

	// ---------- inline variable creation (point of use) ----------

	const NEW_VARIABLE = '__new__';

	// The condition row currently showing the inline creator (at most one at a
	// time); the select isn't bound, so cancelling just restores it.
	let inlineCreatorCondition = $state<any | null>(null);
	let inlineCreatorKey = $state('');
	let inlineCreatorType = $state('string');

	function handleConditionVariableSelect(condition: any, select: HTMLSelectElement) {
		if (select.value === NEW_VARIABLE) {
			inlineCreatorCondition = condition;
			inlineCreatorKey = '';
			inlineCreatorType = 'string';
			// Restore the visible value; the select is about to be swapped out.
			select.value = String(condition.variable ?? '');
			return;
		}
		condition.variable = select.value;
		onChange();
	}

	function confirmInlineVariable() {
		const key = inlineCreatorKey.trim();
		if (!key || !inlineCreatorCondition) return;
		// A duplicate key returns the existing variable's id: just select it.
		const id = onAddVariable?.(key, inlineCreatorType) ?? null;
		if (id) {
			inlineCreatorCondition.variable = id;
			onChange();
		}
		inlineCreatorCondition = null;
	}

	function cancelInlineVariable() {
		inlineCreatorCondition = null;
	}

	function focusOnMount(node: HTMLElement) {
		node.focus();
	}

	function isDeclaredVariable(key: string): boolean {
		return variables.some((v) => v.key === key);
	}

	// ---------- condition-node branches (node branch condition_groups editor) ----------

	function rootGroup(branch: any) {
		if (!branch.condition_groups?.length) {
			branch.condition_groups = [{ operator: 'and', order: 0, conditions: [], children: [] }];
		}
		return branch.condition_groups[0];
	}

	function addCondition(branch: any) {
		const group = rootGroup(branch);
		group.conditions = [
			...group.conditions,
			{ variable: variables[0]?.id ?? null, op: 'eq', value: '', order: group.conditions.length }
		];
		branch.condition_groups = [...branch.condition_groups];
		onChange();
	}

	function removeCondition(branch: any, index: number) {
		const group = rootGroup(branch);
		// Keep at least one condition row on a conditional branch; delete the whole
		// branch to remove it entirely.
		if (group.conditions.length <= 1) return;
		group.conditions = group.conditions.filter((_: unknown, i: number) => i !== index);
		branch.condition_groups = [...branch.condition_groups];
		onChange();
	}
</script>

{#snippet fieldLabel(text: string)}
	<span class="block text-[10px] font-semibold uppercase tracking-wide text-surface-600-400 mb-1">
		{text}
	</span>
{/snippet}

{#snippet branchConditions(branch: any)}
	<div>
		<div class="flex items-center justify-between mb-1">
			{@render fieldLabel(m.edgeConditions())}
			<button
				type="button"
				aria-label={m.addCondition()}
				class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold disabled:opacity-50"
				onclick={() => addCondition(branch)}
				disabled={!variables.length}
			>
				<i class="fa-solid fa-plus mr-0.5"></i>
			</button>
		</div>
		{#if branch.condition_groups[0]?.conditions.length}
			<div class="space-y-1.5">
				{#each branch.condition_groups[0].conditions as condition, index}
					{#if inlineCreatorCondition === condition}
						<!-- Inline creator swapped in for this row's variable select. -->
						<div class="flex items-center gap-1" data-testid="inline-variable-creator">
							<input
								type="text"
								class="input text-xs flex-1 min-w-0"
								placeholder={m.variableKey()}
								bind:value={inlineCreatorKey}
								use:focusOnMount
								onkeydown={(e) => {
									if (e.key === 'Enter') {
										e.preventDefault();
										confirmInlineVariable();
									} else if (e.key === 'Escape') {
										cancelInlineVariable();
									}
								}}
							/>
							<select class="select text-xs w-16 shrink-0" bind:value={inlineCreatorType}>
								{#each VARIABLE_TYPES as t}
									<option value={t}>{t}</option>
								{/each}
							</select>
							<button
								type="button"
								aria-label={m.addVariable()}
								class="btn-icon preset-tonal w-6 h-6 text-xs shrink-0"
								disabled={!inlineCreatorKey.trim()}
								onclick={confirmInlineVariable}
								data-testid="confirm-inline-variable"
							>
								<i class="fa-solid fa-check"></i>
							</button>
							<button
								type="button"
								aria-label={m.cancel()}
								class="btn-icon preset-tonal w-6 h-6 text-xs shrink-0"
								onclick={cancelInlineVariable}
								data-testid="cancel-inline-variable"
							>
								<i class="fa-solid fa-xmark"></i>
							</button>
						</div>
					{:else}
						<div class="flex items-center gap-1">
							<select
								class="select text-xs flex-1 min-w-0"
								value={condition.variable}
								onchange={(e) => handleConditionVariableSelect(condition, e.currentTarget)}
							>
								{#each variables as variable}
									<option value={variable.id}>{variable.key}</option>
								{/each}
								{#if variables.length}
									<option disabled>──────────</option>
								{/if}
								<option value={NEW_VARIABLE}>+ {m.newVariableOption()}</option>
							</select>
							<select
								class="select text-xs w-20 shrink-0"
								bind:value={condition.op}
								onchange={onChange}
							>
								{#each FILTER_OPS as op}
									<option value={op}>{op}</option>
								{/each}
							</select>
							{#if condition.op !== 'is_null'}
								<input
									type="text"
									class="input text-xs w-16 min-w-0"
									bind:value={condition.value}
									oninput={onChange}
								/>
							{/if}
							<button
								type="button"
								aria-label="Remove condition"
								class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0 disabled:opacity-30 disabled:cursor-default"
								disabled={branch.condition_groups[0].conditions.length <= 1}
								onclick={() => removeCondition(branch, index)}
							>
								<i class="fa-solid fa-xmark"></i>
							</button>
						</div>
					{/if}
				{/each}
				{#if branch.condition_groups[0]?.conditions.length > 1}
					<select
						class="select text-xs w-full"
						bind:value={branch.condition_groups[0].operator}
						onchange={onChange}
					>
						<option value="and">AND</option>
						<option value="or">OR</option>
					</select>
				{/if}
			</div>
		{/if}
	</div>
{/snippet}

<aside
	class="w-72 shrink-0 h-full overflow-y-auto border-l border-surface-200-800 bg-surface-100-900"
	data-testid="workflow-inspector"
	onfocusincapture={trackFocus}
	oninputcapture={trackInput}
>
	{#if selectedNode && nodeDomain}
		<div class="p-3 space-y-3">
			<div class="flex items-center gap-2">
				<span class="badge preset-tonal text-[10px] uppercase">
					{safeTranslate(
						'workflowNode' + nodeDomain.type.charAt(0).toUpperCase() + nodeDomain.type.slice(1)
					)}
				</span>
				{#if nodeDomain.type === 'trigger' && triggerConfig}
					<!-- The subtype is fixed at drop time: changing it would invalidate the
					     node's registration; delete and re-add instead. -->
					<span class="badge preset-tonal-success text-[10px]">
						<i class="fa-solid {TRIGGER_ICONS[triggerConfig.type] ?? 'fa-bolt'} mr-1"></i>
						{TRIGGER_LABELS[triggerConfig.type]?.() ?? triggerConfig.type}
					</span>
				{/if}
				{#if nodeDomain.ref}
					<span class="badge preset-tonal text-[9px] font-mono lowercase" title={m.nodeRef()}>
						{nodeDomain.ref}
					</span>
				{/if}
			</div>

			{#if nodeDomain.type === 'end'}
				<!-- The hazard is wiring several branches into one end node and
					expecting them all to finish. Say what it does, and point at the
					safe alternative right where the confusion happens. -->
				<aside
					class="flex gap-2 rounded-md border border-error-500 bg-error-50-950 p-2 text-xs text-error-700-300"
				>
					<i class="fa-solid fa-circle-stop mt-0.5"></i>
					<span>{m.workflowNodeEndHint()}</span>
				</aside>
			{/if}

			{#if nodeDomain.type !== 'end'}
				<label>
					{@render fieldLabel(m.nodeLabel())}
					<input
						type="text"
						class="input w-full text-sm"
						bind:value={nodeDomain.label}
						oninput={onChange}
					/>
				</label>
				{#if nodeDomain.type === 'trigger' && triggerRegistration}
					<p class="text-[10px] text-warning-600 leading-relaxed">
						<i class="fa-solid fa-triangle-exclamation mr-1"></i>{m.renameTriggerWarning()}
					</p>
				{/if}
			{/if}

			{#if nodeDomain.type === 'condition'}
				<div data-testid="condition-branch-list">
					<div class="flex items-center justify-between mb-1">
						{@render fieldLabel(m.workflowBranches())}
						<button
							type="button"
							class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold"
							onclick={() => onAddBranch?.()}
							data-testid="inspector-add-branch"
						>
							<i class="fa-solid fa-plus mr-0.5"></i>{m.addBranch()}
						</button>
					</div>
					<div class="space-y-2">
						{#each branches as row, index (row.branch.id)}
							<div
								class="rounded-base border border-surface-200-800 bg-surface-50-950 p-2 space-y-1.5"
								data-testid="inspector-branch-row"
							>
								<div class="flex items-center gap-1">
									<div class="flex flex-col shrink-0">
										<button
											type="button"
											aria-label="Move branch up"
											class="text-surface-500 hover:text-surface-700-300 cursor-pointer text-[9px] leading-none disabled:opacity-30 disabled:cursor-default"
											disabled={index === 0}
											onclick={() => onMoveBranch?.(index, -1)}
										>
											<i class="fa-solid fa-chevron-up"></i>
										</button>
										<button
											type="button"
											aria-label="Move branch down"
											class="text-surface-500 hover:text-surface-700-300 cursor-pointer text-[9px] leading-none disabled:opacity-30 disabled:cursor-default"
											disabled={index === branches.length - 1}
											onclick={() => onMoveBranch?.(index, 1)}
										>
											<i class="fa-solid fa-chevron-down"></i>
										</button>
									</div>
									<input
										type="text"
										class="input text-xs flex-1 min-w-0"
										placeholder={row.placeholder}
										bind:value={row.branch.name}
										oninput={onChange}
									/>
									<button
										type="button"
										aria-label="Delete branch"
										class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
										onclick={() => onDeleteBranch?.(row.branch.id)}
									>
										<i class="fa-solid fa-trash"></i>
									</button>
								</div>
								{@render branchConditions(row.branch)}
								{#if !row.wired}
									<p class="text-[10px] italic text-surface-500 leading-relaxed">
										<i class="fa-solid fa-link-slash mr-1"></i>{m.branchUnwired()}
									</p>
								{/if}
							</div>
						{/each}
					</div>

					<!-- Default (otherwise) branch: always present, evaluated last.
					     No conditions, no reorder, no delete. -->
					{#if defaultBranch}
						<div
							class="rounded-base border border-surface-300-700 bg-surface-200-800 p-2 mt-2 space-y-1"
							data-testid="inspector-default-branch"
						>
							{@render fieldLabel(m.branchOtherwise())}
							<input
								type="text"
								class="input text-xs w-full"
								placeholder={m.branchOtherwise()}
								bind:value={defaultBranch.branch.name}
								oninput={onChange}
							/>
							<p class="text-[10px] text-surface-500 leading-relaxed">{m.branchDefaultRuns()}</p>
							{#if !defaultBranch.wired}
								<p class="text-[10px] italic text-surface-500 leading-relaxed">
									<i class="fa-solid fa-link-slash mr-1"></i>{m.branchUnwired()}
								</p>
							{/if}
						</div>
					{/if}

					<p class="text-[10px] text-surface-500 leading-relaxed mt-1.5">
						<i class="fa-solid fa-arrow-down-short-wide mr-1"></i>{m.branchesEvaluationHint()}
					</p>
				</div>
			{/if}

			{#if nodeDomain.type === 'task'}
				<label>
					{@render fieldLabel(m.workflowTaskTemplate())}
					<select
						class="select w-full text-sm"
						bind:value={nodeDomain.task_template}
						onchange={onChange}
					>
						<option value={null}>—</option>
						{#each taskTemplates as template}
							<option value={template.id}>{optionLabel(template)}</option>
						{/each}
					</select>
				</label>
			{/if}

			{#if nodeDomain.type === 'loop' && loopConfig}
				<div>
					{@render fieldLabel(m.forEachItemIn())}
					{#if collectionChoices.length}
						<select
							class="select w-full text-sm"
							value={collectionIsCustom ? '__custom__' : (loopConfig.collection ?? '')}
							onchange={(e) => {
								const chosen = e.currentTarget.value;
								if (chosen === '__custom__') {
									collectionIsCustom = true;
								} else {
									collectionIsCustom = false;
									loopConfig.collection = chosen;
									onChange();
								}
							}}
							data-testid="loop-collection"
						>
							{#if !loopConfig.collection && !collectionIsCustom}
								<option value="">—</option>
							{/if}
							{#each collectionChoices as choice (choice.expr)}
								<option value={choice.expr}>
									{choice.label}{choice.count === null ? '' : ` (${choice.count})`}
								</option>
							{/each}
							<option value="__custom__">{m.customExpression()}</option>
						</select>
					{:else}
						<select class="select w-full text-sm" disabled>
							<option>{m.forEachNoCollections()}</option>
						</select>
					{/if}
					{#if collectionIsCustom || (!collectionChoices.length && loopConfig.collection)}
						<input
							type="text"
							class="input w-full text-sm font-mono mt-1"
							placeholder={'{{nodes.list_items.results}}'}
							bind:value={loopConfig.collection}
							oninput={onChange}
						/>
					{/if}
					{#if collectionPreview?.invalid}
						<p class="text-[10px] text-warning-600 mt-1">
							<i class="fa-solid fa-triangle-exclamation mr-1"></i>{m.forEachNotAList()}
						</p>
					{:else if collectionPreview}
						<p class="text-[10px] text-success-600 mt-1">
							<i class="fa-solid fa-rotate mr-1"></i>{m.forEachPreview({
								count: collectionPreview.count
							})}
						</p>
					{/if}
				</div>

				{#if loopConfig.collection}
					{#if itemChips.length}
						<div>
							<span class="text-[10px] font-semibold uppercase tracking-wide text-surface-500">
								{m.perItemFields()}
							</span>
							<div class="flex flex-wrap gap-1 mt-1">
								{#each itemChips as chip (chip)}
									<button
										type="button"
										class="badge preset-tonal text-[10px] font-mono cursor-pointer hover:preset-filled-primary-500"
										title={'{{item.' + chip + '}}'}
										onclick={() => insertExpression('{{item.' + chip + '}}')}
									>
										{chip}
									</button>
								{/each}
								<button
									type="button"
									class="badge preset-tonal text-[10px] font-mono cursor-pointer hover:preset-filled-primary-500"
									title={'{{index}}'}
									onclick={() => insertExpression('{{index}}')}
								>
									index
								</button>
							</div>
							<p class="text-[10px] text-surface-500 mt-1">{m.perItemChipsHint()}</p>
						</div>
					{:else}
						<p class="text-[10px] text-surface-500">
							{m.forEachHint({ item: '{{item}}', index: '{{index}}' })}
						</p>
					{/if}
				{/if}

				<label>
					{@render fieldLabel(m.loopCollect())}
					<input
						type="text"
						class="input w-full text-sm font-mono"
						placeholder={'{{nodes.create_finding.created_object_id}}'}
						bind:value={loopConfig.collect}
						oninput={onChange}
					/>
					<span class="text-[10px] text-surface-500">{m.loopCollectHint()}</span>
				</label>

				<label>
					{@render fieldLabel(m.onItemFailure())}
					<select
						class="select w-full text-sm"
						value={loopConfig.on_item_error ?? 'continue'}
						onchange={(e) => {
							loopConfig.on_item_error = e.currentTarget.value;
							onChange();
						}}
					>
						<option value="continue">{m.continueCollectErrors()}</option>
						<option value="stop">{m.stopTheRun()}</option>
					</select>
				</label>
			{/if}

			{#if nodeDomain.type === 'action'}
				<label>
					{@render fieldLabel(m.actionType())}
					<select
						class="select w-full text-sm"
						bind:value={actionConfig.type}
						onchange={initActionConfig}
					>
						{#each ACTION_TYPES as actionType}
							<option value={actionType}>{safeTranslate(actionType)}</option>
						{/each}
					</select>
				</label>

				{#if actionConfig.type === 'log'}
					<label>
						{@render fieldLabel(m.logMessage())}
						<input
							type="text"
							class="input w-full text-sm"
							bind:value={actionConfig.message}
							oninput={onChange}
						/>
					</label>
				{:else if actionConfig.type === 'create_object' && actionConfig.fields}
					<label>
						{@render fieldLabel(m.objectToCreate())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.model}
							onchange={resetCreateFields}
						>
							{#each creatableModels as entry (entry.key)}
								<option value={entry.key}>{safeTranslate(entry.key)}</option>
							{/each}
						</select>
					</label>
					<label class="flex items-center gap-1.5 text-xs text-surface-700-300 cursor-pointer">
						<input
							type="checkbox"
							class="checkbox scale-75"
							bind:checked={actionConfig.upsert}
							onchange={onChange}
						/>
						{m.upsertExisting()}
						{#if creatableEntry?.match_on}
							<span class="text-[10px] text-surface-500">(match on {creatableEntry.match_on})</span>
						{/if}
					</label>
					{#each creatableEntry?.fields ?? [] as field (field)}
						<label>
							{@render fieldLabel(safeTranslate(field))}
							{#if field === 'description'}
								<textarea
									class="input w-full text-sm"
									rows="2"
									bind:value={actionConfig.fields[field]}
									oninput={onChange}
								></textarea>
							{:else}
								<input
									type="text"
									class="input w-full text-sm"
									placeholder={field === 'name' ? 'Assess {{vendor_name}}' : ''}
									bind:value={actionConfig.fields[field]}
									oninput={onChange}
								/>
							{/if}
						</label>
					{/each}
					{#each Object.entries(creatableEntry?.fk_fields ?? {}) as [fkName, endpoint] (fkName)}
						<label>
							{@render fieldLabel(safeTranslate(fkName))}
							<select
								class="select w-full text-sm"
								bind:value={actionConfig.fields[fkName]}
								onchange={onChange}
							>
								<option value={''}>—</option>
								{#if fkOptions[endpoint as string]?.length}
									<optgroup label={safeTranslate(endpoint as string)}>
										{#each fkOptions[endpoint as string] as option (option.id)}
											<option value={option.id}>{optionLabel(option)}</option>
										{/each}
									</optgroup>
								{/if}
								{#if variables.length}
									<optgroup label={m.workflowVariables()}>
										{#each variables as variable (variable.id)}
											<option value={'{{' + variable.key + '}}'}>
												{'{{' + variable.key + '}}'}
											</option>
										{/each}
									</optgroup>
								{/if}
							</select>
						</label>
					{/each}
				{:else if actionConfig.type === 'update_object'}
					<label>
						{@render fieldLabel(m.objectToUpdate())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.model}
							onchange={resetUpdateFields}
						>
							{#each updatableModels as entry (entry.key)}
								<option value={entry.key}>{safeTranslate(entry.key)}</option>
							{/each}
						</select>
					</label>
					<label>
						{@render fieldLabel(m.targetObjectId())}
						<input
							type="text"
							class="input w-full text-sm"
							placeholder={'{{payload.object_id}}'}
							bind:value={actionConfig.id}
							oninput={onChange}
						/>
					</label>
					{#each updatableEntry?.fields ?? [] as field (field)}
						{@const allowed = updatableEntry?.allowed_values?.[field]}
						<label>
							{@render fieldLabel(safeTranslate(field))}
							{#if allowed?.length}
								<select
									class="select w-full text-sm"
									bind:value={actionConfig.fields[field]}
									onchange={onChange}
								>
									<option value={''}>—</option>
									{#each allowed as value (value)}
										<option {value}>{safeTranslate(value)}</option>
									{/each}
								</select>
								<span class="text-[10px] text-surface-500">{m.guardedFieldHint()}</span>
							{:else if field === 'description' || field === 'observation'}
								<textarea
									class="input w-full text-sm"
									rows="2"
									bind:value={actionConfig.fields[field]}
									oninput={onChange}
								></textarea>
							{:else}
								<input
									type="text"
									class="input w-full text-sm"
									bind:value={actionConfig.fields[field]}
									oninput={onChange}
								/>
							{/if}
						</label>
					{/each}
					{#if Object.keys(updatableEntry?.m2m_fields ?? {}).length}
						<div>
							<div class="flex items-center justify-between mb-1">
								{@render fieldLabel(m.relations())}
								<button
									type="button"
									class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold disabled:opacity-50"
									onclick={addRelationRow}
									disabled={!unusedRelations.length}
								>
									<i class="fa-solid fa-plus mr-0.5"></i>{m.addRelation()}
								</button>
							</div>
							{#each Object.keys(actionConfig.m2m ?? {}) as name (name)}
								{@const endpoint = updatableEntry?.m2m_fields?.[name]}
								<div class="flex items-center gap-1 mb-1">
									<select
										class="select text-xs w-28 shrink-0 px-1 py-0.5"
										value={name}
										onchange={(e) => renameRelationRow(name, e.currentTarget.value)}
									>
										{#each [name, ...unusedRelations] as option (option)}
											<option value={option}>{safeTranslate(option)}</option>
										{/each}
									</select>
									<select
										class="select text-xs w-20 shrink-0 px-1 py-0.5"
										bind:value={actionConfig.m2m[name].op}
										onchange={onChange}
									>
										{#each updatableEntry?.operations ?? ['add', 'remove', 'set'] as operation (operation)}
											<option value={operation}>{safeTranslate(operation)}</option>
										{/each}
									</select>
									<input
										type="text"
										class="input text-xs flex-1 min-w-0 font-mono"
										placeholder={m.relationValues()}
										bind:value={actionConfig.m2m[name].values}
										oninput={onChange}
									/>
									{#if fkOptions[endpoint as string]?.length}
										<select
											class="select text-xs w-16 shrink-0 px-1 py-0.5"
											value={''}
											onchange={(e) => {
												const picked = e.currentTarget.value;
												if (!picked) return;
												const current = actionConfig.m2m[name].values;
												actionConfig.m2m[name].values = current ? `${current},${picked}` : picked;
												e.currentTarget.value = '';
												onChange();
											}}
										>
											<option value={''}>+</option>
											{#each fkOptions[endpoint as string] as option (option.id)}
												<option value={option.id}>{optionLabel(option)}</option>
											{/each}
										</select>
									{/if}
									<button
										type="button"
										aria-label="Remove link"
										class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
										onclick={() => removeRelationRow(name)}
									>
										<i class="fa-solid fa-xmark"></i>
									</button>
								</div>
							{/each}
						</div>
					{/if}
				{:else if actionConfig.type === 'read_objects'}
					<label>
						{@render fieldLabel(m.objectToRead())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.model}
							onchange={resetReadModel}
						>
							{#each readableModels as entry (entry.key)}
								<option value={entry.key}>{safeTranslate(entry.key)}</option>
							{/each}
						</select>
					</label>
					<label>
						{@render fieldLabel(m.readMode())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.mode}
							onchange={onChange}
						>
							<option value="list">{m.readModeList()}</option>
							<option value="first">{m.readModeFirst()}</option>
						</select>
					</label>

					{@render fieldLabel(m.readFilters())}
					{#if readFilterRawMode}
						<textarea
							class="textarea text-xs font-mono w-full"
							rows="6"
							bind:value={readFilterRawJson}
							oninput={syncReadRawFilters}
						></textarea>
						{#if readFilterRawError}
							<p class="text-[10px] text-error-500">{m.invalidFieldFilters()}</p>
						{/if}
					{:else}
						<div class="flex flex-col gap-2">
							{#each readFilterGroups as group, groupIndex (groupIndex)}
								{#if groupIndex > 0}
									<div class="flex items-center gap-2">
										<hr class="grow border-surface-200-800" />
										<span class="text-[10px] font-semibold uppercase text-surface-500">
											{m.or()}
										</span>
										<hr class="grow border-surface-200-800" />
									</div>
								{/if}
								<div
									class="flex flex-col gap-2 rounded-base border border-surface-200-800 bg-surface-50-950 p-2"
								>
									<div class="flex items-center gap-2">
										<span class="text-[10px] uppercase tracking-wide text-surface-500">
											{m.matchAllConditions()}
										</span>
										<button
											type="button"
											title={m.delete()}
											class="btn-icon preset-tonal w-5 h-5 text-[9px] ml-auto hover:preset-filled-error-500"
											onclick={() => {
												readFilterGroups.splice(groupIndex, 1);
												syncReadFilters();
											}}
										>
											<i class="fa-solid fa-trash"></i>
										</button>
									</div>
									{#each group as condition, conditionIndex (conditionIndex)}
										<div
											class="flex flex-col gap-1.5 rounded-base border border-surface-200-800 p-1.5"
										>
											<div class="flex items-center gap-1">
												<select
													class="select text-xs flex-1 min-w-0"
													bind:value={condition.field}
													onchange={syncReadFilters}
												>
													{#if !condition.field}
														<option value="">—</option>
													{/if}
													{#each readableEntry?.fields ?? [] as field (field)}
														<option value={field}>{field}</option>
													{/each}
												</select>
												<select
													class="select text-xs w-24 shrink-0"
													bind:value={condition.op}
													onchange={syncReadFilters}
												>
													{#each FILTER_OPS as op (op)}
														<option value={op}>{op}</option>
													{/each}
												</select>
												<button
													type="button"
													title={m.delete()}
													aria-label={m.delete()}
													class="btn-icon preset-tonal w-5 h-5 text-[9px] shrink-0 hover:preset-filled-error-500"
													onclick={() => {
														group.splice(conditionIndex, 1);
														syncReadFilters();
													}}
												>
													<i class="fa-solid fa-xmark"></i>
												</button>
											</div>
											{#if condition.op !== 'is_null'}
												<input
													type="text"
													class="input text-xs w-full"
													placeholder={'{{payload.id}}'}
													bind:value={condition.value}
													oninput={syncReadFilters}
												/>
											{/if}
										</div>
									{/each}
									<button
										type="button"
										class="btn preset-tonal text-[10px] self-start"
										onclick={() => {
											group.push(newCondition());
											syncReadFilters();
										}}
									>
										<i class="fa-solid fa-plus mr-1"></i>{m.addCondition()}
									</button>
								</div>
							{/each}
							<button
								type="button"
								class="btn preset-tonal text-[10px] self-start"
								onclick={() => {
									readFilterGroups.push([newCondition()]);
									syncReadFilters();
								}}
							>
								<i class="fa-solid fa-plus mr-1"></i>{m.addConditionGroup()}
							</button>
						</div>
					{/if}

					<div class="flex items-end gap-2">
						<label class="flex-1 min-w-0">
							{@render fieldLabel(m.orderBy())}
							<select
								class="select w-full text-sm"
								value={readOrderField}
								onchange={(e) => setReadOrder(e.currentTarget.value, readOrderDesc)}
							>
								{#each readableEntry?.fields ?? [] as field (field)}
									<option value={field}>{field}</option>
								{/each}
							</select>
						</label>
						{#if actionConfig.mode === 'list'}
							<label class="w-24 shrink-0">
								{@render fieldLabel(m.resultLimit())}
								<input
									type="number"
									min="1"
									max="100"
									class="input w-full text-sm"
									bind:value={actionConfig.limit}
									oninput={onChange}
								/>
							</label>
						{/if}
					</div>
					<label class="flex items-center gap-1.5 text-xs text-surface-700-300 cursor-pointer">
						<input
							type="checkbox"
							class="checkbox scale-75"
							checked={readOrderDesc}
							onchange={(e) => setReadOrder(readOrderField, e.currentTarget.checked)}
						/>
						{m.descending()}
					</label>
				{:else if actionConfig.type === 'http_request'}
					<label>
						{@render fieldLabel(m.httpMethod())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.method}
							onchange={onChange}
						>
							{#each HTTP_METHODS as method}
								<option value={method}>{method}</option>
							{/each}
						</select>
					</label>
					<label>
						{@render fieldLabel(m.httpUrl())}
						<input
							type="text"
							class="input w-full text-sm font-mono"
							placeholder="https://api.acme.com/tickets"
							bind:value={actionConfig.url}
							oninput={onChange}
						/>
					</label>
					<div>
						<div class="flex items-center justify-between mb-1">
							{@render fieldLabel(m.httpHeaders())}
							<button
								type="button"
								class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold"
								onclick={addHeaderRow}
							>
								<i class="fa-solid fa-plus mr-0.5"></i>{m.addHeader()}
							</button>
						</div>
						{#each headerEntries as entry, index (index)}
							<div class="flex items-center gap-1 mb-1">
								<input
									type="text"
									class="input text-xs w-24 min-w-0 font-mono shrink-0"
									placeholder="Header"
									bind:value={entry.key}
									oninput={syncHeaders}
								/>
								<input
									type="text"
									class="input text-xs flex-1 min-w-0 font-mono"
									bind:value={entry.value}
									oninput={syncHeaders}
								/>
								<button
									type="button"
									aria-label="Remove header"
									class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
									onclick={() => removeHeaderRow(index)}
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							</div>
						{/each}
					</div>
					<label>
						{@render fieldLabel(m.httpBody())}
						<textarea
							class="input w-full text-sm font-mono"
							rows="3"
							bind:value={actionConfig.body}
							oninput={onChange}
						></textarea>
					</label>
					<label>
						{@render fieldLabel(m.httpTimeout())}
						<input
							type="number"
							class="input w-full text-sm"
							min="1"
							max="30"
							bind:value={actionConfig.timeout}
							oninput={onChange}
						/>
					</label>
					<p class="text-[10px] text-surface-500 leading-relaxed">
						<i class="fa-solid fa-key mr-1"></i>{m.secretsHint({ syntax: '{{secrets.name}}' })}
					</p>
				{:else if actionConfig.type === 'send_email'}
					<label>
						{@render fieldLabel(m.emailRecipients())}
						<input
							type="text"
							class="input w-full text-sm"
							placeholder="ciso@acme.com, {'{{contact_email}}'}"
							bind:value={actionConfig.recipients}
							oninput={onChange}
						/>
					</label>
					<label>
						{@render fieldLabel(m.emailSubject())}
						<input
							type="text"
							class="input w-full text-sm"
							bind:value={actionConfig.subject}
							oninput={onChange}
						/>
					</label>
					<label>
						{@render fieldLabel(m.emailBody())}
						<textarea
							class="input w-full text-sm"
							rows="3"
							bind:value={actionConfig.body}
							oninput={onChange}
						></textarea>
					</label>
				{:else if actionConfig.type === 'provision_folder'}
					<label>
						{@render fieldLabel(m.provisionFolderName())}
						<input
							type="text"
							class="input w-full text-sm"
							placeholder={'HR — {{department}}'}
							bind:value={actionConfig.name}
							oninput={onChange}
						/>
					</label>
					<label>
						{@render fieldLabel(m.parentFolder())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.parent}
							onchange={onChange}
						>
							<option value={''}>—</option>
							{#if fkOptions['folders']?.length}
								<optgroup label={safeTranslate('folders')}>
									{#each fkOptions['folders'] as option (option.id)}
										<option value={option.id}>{optionLabel(option)}</option>
									{/each}
								</optgroup>
							{/if}
							{#if variables.length}
								<optgroup label={m.workflowVariables()}>
									{#each variables as variable (variable.id)}
										<option value={'{{' + variable.key + '}}'}>
											{'{{' + variable.key + '}}'}
										</option>
									{/each}
								</optgroup>
							{/if}
						</select>
					</label>
					<label class="flex items-center gap-1.5 text-xs text-surface-700-300 cursor-pointer">
						<input
							type="checkbox"
							class="checkbox scale-75"
							bind:checked={actionConfig.create_default_groups}
							onchange={onChange}
						/>
						{m.createDefaultGroups()}
					</label>
				{:else if actionConfig.type === 'provision_user'}
					<label>
						{@render fieldLabel(m.userEmail())}
						<input
							type="text"
							class="input w-full text-sm"
							placeholder="jane@acme.com or {'{{contact_email}}'}"
							bind:value={actionConfig.email}
							oninput={onChange}
						/>
					</label>
					<label>
						{@render fieldLabel(m.firstName())}
						<input
							type="text"
							class="input w-full text-sm"
							bind:value={actionConfig.first_name}
							oninput={onChange}
						/>
					</label>
					<label>
						{@render fieldLabel(m.lastName())}
						<input
							type="text"
							class="input w-full text-sm"
							bind:value={actionConfig.last_name}
							oninput={onChange}
						/>
					</label>
					<label class="flex items-center gap-1.5 text-xs text-surface-700-300 cursor-pointer">
						<input
							type="checkbox"
							class="checkbox scale-75"
							bind:checked={actionConfig.is_active}
							onchange={onChange}
						/>
						{m.isActiveUser()}
					</label>
					<label class="flex items-center gap-1.5 text-xs text-surface-700-300 cursor-pointer">
						<input
							type="checkbox"
							class="checkbox scale-75"
							bind:checked={actionConfig.send_onboarding_email}
							onchange={onChange}
						/>
						{m.sendOnboardingEmail()}
					</label>
				{:else if actionConfig.type === 'manage_group_membership'}
					<label>
						{@render fieldLabel(m.membershipUser())}
						<input
							type="text"
							class="input w-full text-sm"
							placeholder="jane@acme.com or {'{{contact_email}}'}"
							bind:value={actionConfig.user}
							oninput={onChange}
						/>
					</label>
					<label>
						{@render fieldLabel(m.folder())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.folder}
							onchange={onChange}
						>
							<option value={''}>—</option>
							{#if fkOptions['folders']?.length}
								<optgroup label={safeTranslate('folders')}>
									{#each fkOptions['folders'] as option (option.id)}
										<option value={option.id}>{optionLabel(option)}</option>
									{/each}
								</optgroup>
							{/if}
							{#if variables.length}
								<optgroup label={m.workflowVariables()}>
									{#each variables as variable (variable.id)}
										<option value={'{{' + variable.key + '}}'}>
											{'{{' + variable.key + '}}'}
										</option>
									{/each}
								</optgroup>
							{/if}
						</select>
					</label>
					<div class="grid grid-cols-2 gap-2">
						<label>
							{@render fieldLabel(m.builtinGroup())}
							<select
								class="select w-full text-xs"
								bind:value={actionConfig.builtin_group}
								onchange={onChange}
							>
								{#each BUILTIN_GROUPS as group (group.code)}
									<option value={group.code}>{safeTranslate(group.label)}</option>
								{/each}
							</select>
						</label>
						<label>
							{@render fieldLabel(m.membershipOperation())}
							<select
								class="select w-full text-xs"
								bind:value={actionConfig.operation}
								onchange={onChange}
							>
								<option value="add">{m.operationAdd()}</option>
								<option value="remove">{m.operationRemove()}</option>
							</select>
						</label>
					</div>
				{:else if actionConfig.type === 'emit_event'}
					<label>
						{@render fieldLabel(m.eventKey())}
						<input
							type="text"
							class="input w-full text-sm font-mono"
							placeholder="questionnaire_submitted"
							bind:value={actionConfig.event_key}
							oninput={onChange}
						/>
					</label>
				{:else if actionConfig.type === 'set_variables' && actionConfig.variables}
					<div>
						<div class="flex items-center justify-between mb-1">
							{@render fieldLabel(m.workflowVariables())}
							<button
								type="button"
								class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold disabled:opacity-50"
								onclick={addSetVariableRow}
								disabled={!variables.length}
							>
								<i class="fa-solid fa-plus"></i>
							</button>
						</div>
						{#each Object.keys(actionConfig.variables) as key (key)}
							<div class="flex items-center gap-1 mb-1">
								<select
									class="select text-xs font-mono w-24 shrink-0 px-1 py-0.5"
									value={key}
									onchange={(e) => renameSetVariableRow(key, e.currentTarget.value)}
									data-testid="set-variable-key"
								>
									{#each mappingKeyOptions(actionConfig.variables, key) as option (option)}
										<option value={option}>{option}</option>
									{/each}
								</select>
								<input
									type="text"
									class="input text-xs flex-1 min-w-0"
									bind:value={actionConfig.variables[key]}
									oninput={onChange}
								/>
								<button
									type="button"
									aria-label="Remove"
									class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
									onclick={() => removeSetVariableRow(key)}
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							</div>
						{/each}
					</div>
				{:else if actionConfig.type === 'date_offset'}
					<label>
						{@render fieldLabel(m.dateOffsetBase())}
						<input
							type="text"
							class="input w-full text-sm"
							placeholder={'{{today}}'}
							bind:value={actionConfig.base}
							oninput={onChange}
						/>
					</label>
					<div class="flex gap-2">
						<label class="flex-1">
							{@render fieldLabel(m.days())}
							<input
								type="number"
								class="input w-full text-sm"
								bind:value={actionConfig.days}
								oninput={onChange}
							/>
						</label>
						<label class="flex-1">
							{@render fieldLabel(m.weeks())}
							<input
								type="number"
								class="input w-full text-sm"
								bind:value={actionConfig.weeks}
								oninput={onChange}
							/>
						</label>
					</div>
					<label>
						{@render fieldLabel(m.dateOffsetStoreIn())}
						<select
							class="select w-full text-sm"
							bind:value={actionConfig.output}
							onchange={onChange}
						>
							<option value={''}>—</option>
							{#each variables as variable (variable.id)}
								<option value={variable.key}>{variable.key}</option>
							{/each}
						</select>
					</label>
					<p class="text-[10px] text-surface-500 leading-relaxed">
						<i class="fa-solid fa-calendar-day mr-1"></i>{m.dateOffsetHint()}
					</p>
				{/if}
				<p class="text-[10px] text-surface-500 leading-relaxed">
					<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{m.templatingHint({
						syntax: '{{variable}}'
					})}
				</p>
			{/if}

			{#if ['action', 'subprocess', 'loop'].includes(nodeDomain.type)}
				<div>
					<div class="flex items-center justify-between mb-1">
						{@render fieldLabel(m.outputMapping())}
						<button
							type="button"
							class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold disabled:opacity-50"
							onclick={addOutputMapping}
							disabled={!variables.length}
						>
							<i class="fa-solid fa-plus mr-0.5"></i>{m.addMapping()}
						</button>
					</div>
					{#each Object.keys(nodeDomain.output_mapping ?? {}) as key (key)}
						<div class="flex items-center gap-1 mb-1">
							<select
								class="select text-xs font-mono w-24 shrink-0 px-1 py-0.5"
								value={key}
								onchange={(e) => renameOutputMapping(key, e.currentTarget.value)}
								data-testid="output-mapping-variable"
							>
								{#each mappingKeyOptions(nodeDomain.output_mapping, key) as option (option)}
									<option value={option}>{option}</option>
								{/each}
							</select>
							<i class="fa-solid fa-arrow-left text-[9px] text-surface-500 shrink-0"></i>
							<input
								type="text"
								class="input text-xs flex-1 min-w-0 font-mono"
								placeholder={m.outputPath()}
								bind:value={nodeDomain.output_mapping[key]}
								oninput={onChange}
							/>
							<button
								type="button"
								aria-label="Remove mapping"
								class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
								onclick={() => removeOutputMapping(key)}
							>
								<i class="fa-solid fa-xmark"></i>
							</button>
						</div>
					{/each}
					<p class="text-[10px] text-surface-500 leading-relaxed">
						{m.outputMappingHint({ example: outputExample })}
					</p>
				</div>
			{/if}

			{#if nodeDomain.type === 'trigger' && triggerConfig}
				{#if triggerConfig.type === 'schedule'}
					<label>
						{@render fieldLabel(m.cronExpression())}
						<input
							type="text"
							class="input w-full text-sm font-mono"
							placeholder="0 3 * * *"
							bind:value={triggerConfig.cron_expression}
							oninput={onChange}
							data-testid="trigger-cron"
						/>
					</label>
					<label>
						{@render fieldLabel(m.scheduleTimezone())}
						<input
							type="text"
							class="input w-full text-sm"
							placeholder="UTC"
							bind:value={triggerConfig.timezone}
							oninput={onChange}
							data-testid="trigger-timezone"
						/>
					</label>
					<p class="text-[10px] text-surface-500 leading-relaxed">
						{m.cronExpressionHint()}
					</p>
				{:else if triggerConfig.type === 'internal_event'}
					<label>
						{@render fieldLabel(m.whenThisHappens())}
						<select
							class="select w-full text-sm"
							bind:value={triggerConfig.event_key}
							onchange={onChange}
							data-testid="trigger-event-key"
						>
							<option value="" disabled hidden></option>
							{#each eventKeysByModel as [model, keys] (model)}
								<optgroup label={safeTranslate(model)}>
									{#each keys as ek (ek.key)}
										<option value={ek.key}>{ek.action}</option>
									{/each}
								</optgroup>
							{/each}
						</select>
					</label>

					{#if filterRawMode}
						<label>
							{@render fieldLabel(m.rawJsonFilters())}
							<textarea
								class="textarea text-xs font-mono w-full"
								rows="6"
								bind:value={filterRawJson}
								oninput={syncRawFilters}
							></textarea>
						</label>
						{#if filterRawError}
							<p class="text-[10px] text-error-500">{m.invalidFieldFilters()}</p>
						{/if}
					{:else}
						<div class="flex flex-col gap-2">
							<span class="text-[10px] font-semibold uppercase tracking-wide text-surface-600-400">
								{m.matchAnyGroup()}
							</span>
							{#each filterGroups as group, groupIndex (groupIndex)}
								{#if groupIndex > 0}
									<div class="flex items-center gap-2">
										<hr class="grow border-surface-200-800" />
										<span class="text-[10px] font-semibold uppercase text-surface-500">
											{m.or()}
										</span>
										<hr class="grow border-surface-200-800" />
									</div>
								{/if}
								<div
									class="flex flex-col gap-2 rounded-base border border-surface-200-800 bg-surface-50-950 p-2"
								>
									<div class="flex items-center gap-2">
										<span class="text-[10px] uppercase tracking-wide text-surface-500">
											{m.matchAllConditions()}
										</span>
										<button
											type="button"
											title={m.delete()}
											class="btn-icon preset-tonal w-5 h-5 text-[9px] ml-auto hover:preset-filled-error-500"
											onclick={() => {
												filterGroups.splice(groupIndex, 1);
												syncFilters();
											}}
										>
											<i class="fa-solid fa-trash"></i>
										</button>
									</div>
									{#each group as condition, conditionIndex (conditionIndex)}
										<div
											class="flex flex-col gap-1.5 rounded-base border border-surface-200-800 p-1.5"
										>
											<div class="flex gap-1">
												{#each FIELD_CHIPS as chip (chip)}
													<button
														type="button"
														class="badge preset-tonal text-[9px] cursor-pointer"
														onclick={() => {
															condition.field = chip;
															syncFilters();
														}}
													>
														{chip}
													</button>
												{/each}
												<button
													type="button"
													title={m.delete()}
													aria-label={m.delete()}
													class="btn-icon preset-tonal w-5 h-5 text-[9px] ml-auto hover:preset-filled-error-500"
													onclick={() => {
														group.splice(conditionIndex, 1);
														syncFilters();
													}}
												>
													<i class="fa-solid fa-xmark"></i>
												</button>
											</div>
											<div class="flex items-center gap-1">
												<input
													type="text"
													class="input text-xs flex-1 min-w-0 font-mono"
													bind:value={condition.field}
													oninput={syncFilters}
												/>
												<select
													class="select text-xs w-24 shrink-0"
													bind:value={condition.op}
													onchange={syncFilters}
												>
													{#each FILTER_OPS as op (op)}
														<option value={op}>{op}</option>
													{/each}
												</select>
											</div>
											{#if condition.op !== 'is_null'}
												{#if condition.field === 'folder'}
													<select
														class="select text-xs w-full"
														bind:value={condition.value}
														onchange={syncFilters}
													>
														{#each fkOptions['folders'] ?? [] as folder (folder.id)}
															<option value={folder.id}>{optionLabel(folder)}</option>
														{/each}
													</select>
												{:else}
													<input
														type="text"
														class="input text-xs w-full"
														bind:value={condition.value}
														oninput={syncFilters}
													/>
												{/if}
											{/if}
											<label
												class="flex items-center gap-1 text-[10px] text-surface-500"
												title={CHANGED_HELP}
											>
												<input
													type="checkbox"
													class="checkbox scale-75"
													bind:checked={condition.changed}
													onchange={syncFilters}
												/>
												{m.onlyWhenChanged()}
											</label>
										</div>
									{/each}
									<button
										type="button"
										class="btn preset-tonal text-[10px] self-start"
										onclick={() => {
											group.push(newCondition());
											syncFilters();
										}}
									>
										<i class="fa-solid fa-plus mr-1"></i>{m.addCondition()}
									</button>
								</div>
							{/each}
							<button
								type="button"
								class="btn preset-tonal text-[10px] self-start"
								onclick={() => {
									filterGroups.push([newCondition()]);
									syncFilters();
								}}
							>
								<i class="fa-solid fa-plus mr-1"></i>{m.addConditionGroup()}
							</button>
						</div>
					{/if}
				{:else if triggerConfig.type === 'webhook'}
					{#if triggerRegistration && nodeHookUrl}
						<div>
							{@render fieldLabel(m.webhookTrigger())}
							<div class="flex items-center gap-1">
								<input
									type="text"
									class="input w-full text-[10px] font-mono"
									readonly
									value={nodeHookUrl}
								/>
								<button
									type="button"
									aria-label="Copy webhook URL"
									class="btn-icon preset-tonal w-7 h-7 text-xs shrink-0"
									onclick={copyHookUrl}
								>
									<i class="fa-solid {copiedHook ? 'fa-check text-success-500' : 'fa-copy'}"></i>
								</button>
								<button
									type="button"
									title={m.rotateSecret()}
									aria-label={m.rotateSecret()}
									class="btn-icon preset-tonal w-7 h-7 text-xs shrink-0"
									onclick={rotateSecret}
									data-testid="rotate-trigger-secret"
								>
									<i class="fa-solid fa-rotate"></i>
								</button>
							</div>
							<p class="text-[10px] text-surface-500 mt-1 leading-relaxed">
								{m.webhookUrlHintNode()}
							</p>
						</div>
					{:else}
						<p class="text-[10px] text-surface-500 leading-relaxed">
							<i class="fa-solid fa-satellite-dish mr-1"></i>{m.publishToObtainHookUrl()}
						</p>
					{/if}
				{/if}

				<div>
					<div class="flex items-center justify-between mb-1">
						{@render fieldLabel(m.payloadMapping())}
						<button
							type="button"
							class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold disabled:opacity-50"
							onclick={addInputMapping}
							disabled={!variables.length}
						>
							<i class="fa-solid fa-plus mr-0.5"></i>{m.addMapping()}
						</button>
					</div>
					{#each Object.keys(nodeDomain.input_mapping ?? {}) as key (key)}
						<div class="flex items-center gap-1 mb-1">
							<select
								class="select text-xs font-mono w-24 shrink-0 px-1 py-0.5"
								value={key}
								onchange={(e) => renameInputMapping(key, e.currentTarget.value)}
								data-testid="input-mapping-variable"
							>
								{#each mappingKeyOptions(nodeDomain.input_mapping, key) as option (option)}
									<option value={option}>{option}</option>
								{/each}
							</select>
							{#if !isDeclaredVariable(key)}
								<!-- Assist, not a blocker: the key maps to no declared variable. -->
								<span
									class="flex items-center gap-1 text-[9px] text-warning-600 shrink-0"
									title={m.undeclaredVariable()}
									data-testid="undeclared-variable-chip"
								>
									<i class="fa-solid fa-circle-exclamation"></i>
									{m.undeclaredVariable()}
									<button
										type="button"
										class="badge preset-tonal-warning text-[9px] cursor-pointer"
										onclick={() => onAddVariable?.(key, 'string')}
										data-testid="declare-variable"
									>
										{m.declareVariable()}
									</button>
								</span>
							{/if}
							<i class="fa-solid fa-arrow-left text-[9px] text-surface-500 shrink-0"></i>
							<input
								type="text"
								class="input text-xs flex-1 min-w-0 font-mono"
								placeholder={m.payloadPath()}
								bind:value={nodeDomain.input_mapping[key]}
								oninput={onChange}
							/>
							<button
								type="button"
								aria-label="Remove mapping"
								class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
								onclick={() => removeInputMapping(key)}
							>
								<i class="fa-solid fa-xmark"></i>
							</button>
						</div>
					{/each}
					{#if !variables.length}
						<p class="text-[10px] text-surface-500">{m.workflowVariables()}: 0</p>
					{/if}
				</div>
			{/if}

			{#if nodeDomain.type === 'subprocess'}
				<label>
					{@render fieldLabel(m.subprocessWorkflow())}
					<select
						class="select w-full text-sm"
						bind:value={nodeDomain.subprocess_workflow}
						onchange={onChange}
					>
						<option value={null}>—</option>
						{#each subprocessCandidates as candidate}
							<option value={candidate.id}>{optionLabel(candidate)}</option>
						{/each}
					</select>
				</label>
			{/if}

			{#if nodeDomain.type === 'event'}
				<label>
					{@render fieldLabel(m.eventKey())}
					<input
						type="text"
						class="input w-full text-sm font-mono"
						placeholder="questionnaire_submitted"
						bind:value={nodeDomain.event_key}
						oninput={onChange}
					/>
				</label>
			{/if}

			<div class="pt-2 border-t border-surface-200-800">
				<div class="flex items-center justify-between mb-1">
					{@render fieldLabel(m.availableData())}
					{#if copiedExpression}
						<span class="text-[9px] text-success-600">{m.copied()}</span>
					{/if}
				</div>
				{#if livePreview !== null}
					<p
						class="text-[10px] font-mono bg-surface-50-950 border border-surface-200-800 rounded px-1.5 py-1 mb-2 break-all"
					>
						<span class="text-surface-500">{m.previewLabel()}:</span>
						<span class="text-success-600 dark:text-success-400">{livePreview}</span>
					</p>
				{/if}
				{#if referenceRunId}
					<DataBrowser
						variables={referenceVariables}
						nodes={referenceNodes}
						{secretNames}
						onInsert={insertExpression}
						onAddSecret={readonly ? undefined : onAddSecret}
						itemPreview={collectionPreview && !collectionPreview.invalid
							? collectionPreview.first
							: undefined}
					/>
					<p class="text-[9px] text-surface-500 mt-1 leading-relaxed">
						<i class="fa-solid fa-arrow-pointer mr-1"></i>{m.insertHint()}
					</p>
				{:else}
					<p class="text-[10px] text-surface-500 leading-relaxed">
						{m.noReferenceRun()}
					</p>
				{/if}
			</div>
		</div>
	{:else if selectedEdge && edgeDomain}
		<div class="p-3 space-y-3">
			<span class="badge preset-tonal text-[10px] uppercase">
				<i class="fa-solid fa-arrow-right-long mr-1"></i>{m.edgeLabel()}
			</span>

			<!-- Condition-sourced edges never reach this block (the canvas redirects
			     their selection to the switch block), so only the label remains. -->
			<label>
				{@render fieldLabel(m.edgeLabel())}
				<input
					type="text"
					class="input w-full text-sm"
					bind:value={edgeDomain.label}
					oninput={onChange}
				/>
			</label>
		</div>
	{/if}
</aside>
