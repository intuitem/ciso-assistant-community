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
	import DataBrowser from './DataBrowser.svelte';
	import { renderTemplate } from './expressions';
	import { TRIGGER_ICONS } from './nodes/TriggerNode.svelte';
	import { newCondition, treeToGroups, groupsToTree, type Condition } from './filter-dnf';

	interface Option {
		id: string;
		name?: string;
		str?: string;
		code?: string;
	}

	interface Props {
		selectedNode: any | null;
		selectedEdge: any | null;
		variables: { id: string; key: string; type: string }[];
		roles: Option[];
		actors: Option[];
		taskTemplates: Option[];
		subprocessCandidates: Option[];
		creatableModels?: any[];
		fkOptions?: Record<string, Option[]>;
		workflowId: string;
		registrationsByRef?: Record<string, any>;
		onRegistrationsChanged?: () => void;
		referenceRunId?: string | null;
		referenceVariables?: Record<string, unknown>;
		referenceNodes?: { key: string; label: string; output: unknown }[];
		secretNames?: string[];
		onChange: () => void;
	}

	let {
		selectedNode = $bindable(),
		selectedEdge = $bindable(),
		variables,
		roles,
		actors,
		taskTemplates,
		subprocessCandidates,
		creatableModels = [],
		fkOptions = {},
		workflowId,
		registrationsByRef = {},
		onRegistrationsChanged,
		referenceRunId = null,
		referenceVariables = {},
		referenceNodes = [],
		secretNames = [],
		onChange
	}: Props = $props();

	// ---------- expression assist (spec D20) ----------

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
		node: Object.fromEntries(referenceNodes.map((n) => [n.key, n.output])),
		secrets: Object.fromEntries(secretNames.map((name) => [name, '•••']))
	});
	const livePreview = $derived(
		lastFocusedValue.includes('{{') ? renderTemplate(lastFocusedValue, previewContext) : null
	);

	// emit_event is hidden pending the event-node redesign (correlation +
	// buffering); the engine still executes it for graphs that carry it.
	const ACTION_TYPES = [
		'create_object',
		'http_request',
		'send_email',
		'provision_folder',
		'provision_user',
		'manage_group_membership',
		'set_variables',
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

	const CONDITION_OPS = [
		'eq',
		'neq',
		'gt',
		'lt',
		'gte',
		'lte',
		'in',
		'not_in',
		'contains',
		'is_null'
	];

	const nodeDomain = $derived(selectedNode?.data?.domain);
	const edgeDomain = $derived(selectedEdge?.data?.domain);
	const actionConfig = $derived(nodeDomain?.action_config);

	const ACTION_CONFIG_DEFAULTS: Record<string, object> = {
		log: { message: '' },
		set_variables: { variables: {} },
		create_object: { model: 'applied_control', fields: { name: '' }, upsert: false },
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

	function resetCreateFields() {
		actionConfig.fields = { name: actionConfig.fields?.name ?? '' };
		onChange();
	}

	function initActionConfig() {
		const type = actionConfig.type;
		const defaults: any = ACTION_CONFIG_DEFAULTS[type] ?? {};
		for (const [key, value] of Object.entries(defaults)) {
			if (actionConfig[key] === undefined) actionConfig[key] = value;
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
		if (['action', 'subprocess'].includes(nodeDomain?.type) && !nodeDomain.output_mapping) {
			nodeDomain.output_mapping = {};
		}
	});

	// What a path into this step's output typically looks like, for the hint.
	const OUTPUT_EXAMPLES: Record<string, string> = {
		http_request: 'body.summary',
		create_object: 'created_object_id',
		provision_folder: 'folder_id',
		provision_user: 'user_id',
		manage_group_membership: 'group_id',
		send_email: 'subject',
		log: 'message'
	};
	const outputExample = $derived(
		nodeDomain?.type === 'subprocess'
			? 'a child workflow variable key'
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
	const nodeHookUrl = $derived(
		triggerRegistration && triggerConfig?.type === 'webhook'
			? `${location.origin}/api/workflows/hooks/${workflowId}/${nodeDomain.ref}/${triggerRegistration.secret}/`
			: null
	);

	function triggerOps(action: string, body: Record<string, unknown>) {
		return fetch(`/workflows/${workflowId}/ops?action=${action}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
	}

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
		if (res.ok) onRegistrationsChanged?.();
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

	const FILTER_OPS = ['eq', 'neq', 'gt', 'lt', 'gte', 'lte', 'in', 'not_in', 'contains', 'is_null'];
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

	function addAssignment() {
		nodeDomain.assignments = [
			...nodeDomain.assignments,
			{
				role: roles[0]?.id ?? null,
				role_code: roles[0]?.code ?? '',
				actor: null,
				resolve_type: 'actor',
				variable_key: '',
				is_blocking: true,
				participation: 'task'
			}
		];
		onChange();
	}

	function removeAssignment(index: number) {
		nodeDomain.assignments = nodeDomain.assignments.filter((_: unknown, i: number) => i !== index);
		onChange();
	}

	function syncRoleCode(assignment: any) {
		const role = roles.find((r) => r.id === assignment.role);
		assignment.role_code = role?.code ?? '';
		onChange();
	}

	function rootGroup() {
		if (!edgeDomain.condition_groups.length) {
			edgeDomain.condition_groups = [{ operator: 'and', order: 0, conditions: [], children: [] }];
		}
		return edgeDomain.condition_groups[0];
	}

	function addCondition() {
		const group = rootGroup();
		group.conditions = [
			...group.conditions,
			{ variable: variables[0]?.id ?? null, op: 'eq', value: '', order: group.conditions.length }
		];
		edgeDomain.condition_groups = [...edgeDomain.condition_groups];
		onChange();
	}

	function removeCondition(index: number) {
		const group = rootGroup();
		group.conditions = group.conditions.filter((_: unknown, i: number) => i !== index);
		if (!group.conditions.length) edgeDomain.condition_groups = [];
		else edgeDomain.condition_groups = [...edgeDomain.condition_groups];
		onChange();
	}
</script>

{#snippet fieldLabel(text: string)}
	<span class="block text-[10px] font-semibold uppercase tracking-wide text-surface-600-400 mb-1">
		{text}
	</span>
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
								<span class="text-xs font-mono w-24 truncate shrink-0">{key}</span>
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
				{/if}
				<p class="text-[10px] text-surface-500 leading-relaxed">
					<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{m.templatingHint({
						syntax: '{{variable}}'
					})}
				</p>
			{/if}

			{#if ['action', 'subprocess'].includes(nodeDomain.type)}
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
							<span class="text-xs font-mono w-24 truncate shrink-0">{key}</span>
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
							<span class="text-xs font-mono w-24 truncate shrink-0">{key}</span>
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

			{#if nodeDomain.type !== 'end'}
				<div class="grid grid-cols-2 gap-2">
					<label>
						{@render fieldLabel(m.forkType())}
						<select
							class="select w-full text-xs"
							bind:value={nodeDomain.fork_type}
							onchange={onChange}
						>
							<option value="exclusive">{m.forkExclusive()}</option>
							<option value="parallel">{m.forkParallel()}</option>
						</select>
					</label>
					{#if nodeDomain.type !== 'trigger'}
						<!-- Trigger nodes cannot have incoming edges, so a join makes no sense. -->
						<label>
							{@render fieldLabel(m.joinType())}
							<select
								class="select w-full text-xs"
								bind:value={nodeDomain.join_type}
								onchange={onChange}
							>
								<option value="none">{m.joinNone()}</option>
								<option value="and">{m.joinAnd()}</option>
								<option value="or">{m.joinOr()}</option>
							</select>
						</label>
					{/if}
				</div>
			{/if}

			{#if ['task', 'action', 'subprocess'].includes(nodeDomain.type)}
				<div>
					<div class="flex items-center justify-between mb-1">
						{@render fieldLabel(m.nodeAssignments())}
						<button
							type="button"
							class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold"
							onclick={addAssignment}
						>
							<i class="fa-solid fa-plus mr-0.5"></i>{m.addAssignment()}
						</button>
					</div>
					<div class="space-y-2">
						{#each nodeDomain.assignments as assignment, index}
							<div
								class="rounded-base border border-surface-200-800 bg-surface-50-950 p-2 space-y-1.5"
							>
								<div class="flex items-center gap-1.5">
									<select
										class="select text-xs w-20 shrink-0"
										bind:value={assignment.role}
										onchange={() => syncRoleCode(assignment)}
									>
										{#each roles as role}
											<option value={role.id}>{role.code}</option>
										{/each}
									</select>
									<select
										class="select text-xs flex-1 min-w-0"
										bind:value={assignment.actor}
										onchange={onChange}
									>
										<option value={null}>—</option>
										{#each actors as actor}
											<option value={actor.id}>{optionLabel(actor)}</option>
										{/each}
									</select>
									<button
										type="button"
										aria-label="Remove assignment"
										class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
										onclick={() => removeAssignment(index)}
									>
										<i class="fa-solid fa-xmark"></i>
									</button>
								</div>
								<div class="flex items-center gap-3 text-[10px] text-surface-700-300">
									<label class="flex items-center gap-1 cursor-pointer">
										<input
											type="checkbox"
											class="checkbox scale-75"
											bind:checked={assignment.is_blocking}
											onchange={onChange}
										/>
										{m.blockingAssignment()}
									</label>
									<select
										class="select text-[10px] px-1 py-0.5 flex-1"
										bind:value={assignment.participation}
										onchange={onChange}
									>
										<option value="task">{m.participationTask()}</option>
										<option value="notification">{m.participationNotification()}</option>
									</select>
								</div>
							</div>
						{/each}
					</div>
				</div>
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

			<label>
				{@render fieldLabel(m.edgeLabel())}
				<input
					type="text"
					class="input w-full text-sm"
					bind:value={edgeDomain.label}
					oninput={onChange}
				/>
			</label>

			<label>
				{@render fieldLabel(m.edgePriority())}
				<input
					type="number"
					class="input w-full text-sm"
					bind:value={edgeDomain.priority}
					oninput={onChange}
				/>
			</label>

			<div>
				<div class="flex items-center justify-between mb-1">
					{@render fieldLabel(m.edgeConditions())}
					<button
						type="button"
						class="text-[10px] text-primary-500 hover:text-primary-600 cursor-pointer font-semibold disabled:opacity-50"
						onclick={addCondition}
						disabled={!variables.length}
					>
						<i class="fa-solid fa-plus mr-0.5"></i>
					</button>
				</div>
				{#if !variables.length}
					<p class="text-[10px] text-surface-500">{m.workflowVariables()}: 0</p>
				{/if}
				{#if edgeDomain.condition_groups.length}
					<div class="space-y-1.5">
						{#each edgeDomain.condition_groups[0].conditions as condition, index}
							<div class="flex items-center gap-1">
								<select
									class="select text-xs flex-1 min-w-0"
									bind:value={condition.variable}
									onchange={onChange}
								>
									{#each variables as variable}
										<option value={variable.id}>{variable.key}</option>
									{/each}
								</select>
								<select
									class="select text-xs w-20 shrink-0"
									bind:value={condition.op}
									onchange={onChange}
								>
									{#each CONDITION_OPS as op}
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
									class="text-error-500 hover:text-error-600 cursor-pointer text-xs shrink-0"
									onclick={() => removeCondition(index)}
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							</div>
						{/each}
						{#if edgeDomain.condition_groups[0]?.conditions.length > 1}
							<select
								class="select text-xs w-full"
								bind:value={edgeDomain.condition_groups[0].operator}
								onchange={onChange}
							>
								<option value="and">AND</option>
								<option value="or">OR</option>
							</select>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<div class="p-4 text-center text-surface-500 text-xs mt-8">
			<i class="fa-solid fa-arrow-pointer text-lg mb-2 block opacity-50"></i>
			{m.workflowBuilderHint()}
		</div>
	{/if}
</aside>
