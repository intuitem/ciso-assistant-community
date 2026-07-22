<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Variable {
		id: string;
		key: string;
		type: string;
	}

	interface Secret {
		id: string;
		name: string;
	}

	interface PaletteItem {
		type: string;
		triggerType?: string;
		icon: string;
		label: string;
	}

	interface Props {
		variables: Variable[];
		secrets: Secret[];
		onAdd: (nodeType: string, triggerType?: string) => void;
		onAddVariable: (key: string, type: string) => void;
		onRemoveVariable: (id: string) => void;
		onAddSecret: (name: string, value: string) => void;
		onRemoveSecret: (id: string) => void;
	}

	let {
		variables,
		secrets,
		onAdd,
		onAddVariable,
		onRemoveVariable,
		onAddSecret,
		onRemoveSecret
	}: Props = $props();

	// Task and subprocess nodes are hidden for the MVP (human tasks land with
	// the TaskNode integration; subprocess needs its mapping UI + recursion
	// guard). The engine still executes them for graphs that carry them.
	const TRIGGER_ITEMS = $derived<PaletteItem[]>([
		{ type: 'trigger', triggerType: 'manual', icon: 'fa-hand-pointer', label: m.triggerManual() },
		{
			type: 'trigger',
			triggerType: 'webhook',
			icon: 'fa-satellite-dish',
			label: m.triggerWebhook()
		},
		{ type: 'trigger', triggerType: 'schedule', icon: 'fa-clock', label: m.triggerSchedule() },
		{
			type: 'trigger',
			triggerType: 'internal_event',
			icon: 'fa-rss',
			label: m.triggerInternalEvent()
		}
	]);
	const STEP_ITEMS = $derived<PaletteItem[]>([
		{ type: 'condition', icon: 'fa-code-branch', label: m.workflowNodeCondition() },
		{ type: 'action', icon: 'fa-bolt', label: m.workflowNodeAction() },
		{ type: 'end', icon: 'fa-flag-checkered', label: m.workflowNodeEnd() }
	]);

	let nodeSearch = $state('');
	const GROUPS = $derived(
		[
			{ key: 'triggers', label: m.workflowTriggers(), items: TRIGGER_ITEMS },
			{ key: 'steps', label: m.workflowSteps(), items: STEP_ITEMS }
		]
			.map((group) => ({
				...group,
				items: group.items.filter((item) =>
					item.label.toLowerCase().includes(nodeSearch.trim().toLowerCase())
				)
			}))
			.filter((group) => group.items.length > 0)
	);

	let newVariableKey = $state('');
	let newVariableType = $state('string');

	const VARIABLE_TYPES = ['string', 'number', 'boolean', 'date', 'json'];

	function submitVariable(event: Event) {
		event.preventDefault();
		const key = newVariableKey.trim();
		if (!key) return;
		onAddVariable(key, newVariableType);
		newVariableKey = '';
	}

	let newSecretName = $state('');
	let newSecretValue = $state('');

	function submitSecret(event: Event) {
		event.preventDefault();
		const name = newSecretName.trim();
		if (!name || !newSecretValue) return;
		onAddSecret(name, newSecretValue);
		newSecretName = '';
		newSecretValue = '';
	}

	function handleDragStart(event: DragEvent, item: PaletteItem) {
		event.dataTransfer?.setData(
			'application/ciso-workflow-node',
			JSON.stringify({ type: item.type, triggerType: item.triggerType })
		);
		if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
	}
</script>

<aside
	class="w-52 shrink-0 h-full overflow-y-auto border-r border-surface-200-800 bg-surface-100-900 flex flex-col"
>
	<div class="p-3">
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400 mb-2">
			{m.nodePalette()}
		</h3>
		<div class="relative mb-2">
			<i
				class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-surface-400-600 pointer-events-none"
			></i>
			<input
				type="search"
				class="input w-full text-xs pl-6 pr-1.5 py-1"
				placeholder={m.searchNodeTypes()}
				bind:value={nodeSearch}
				data-testid="palette-search"
			/>
		</div>
		{#each GROUPS as group (group.key)}
			<h4
				class="text-[10px] font-semibold uppercase tracking-wide text-surface-500 mt-2 mb-1.5 first:mt-0"
			>
				{group.label}
			</h4>
			<div class="flex flex-col gap-1.5">
				{#each group.items as item (item.type + (item.triggerType ?? ''))}
					<button
						type="button"
						draggable="true"
						ondragstart={(e) => handleDragStart(e, item)}
						onclick={() => onAdd(item.type, item.triggerType)}
						class="flex items-center gap-2 px-2.5 py-2 rounded-base border border-surface-200-800 bg-surface-50-950 text-xs text-surface-800-200 cursor-grab hover:border-primary-400 hover:shadow-sm transition-all text-left"
						data-testid="palette-{item.triggerType
							? `${item.type}-${item.triggerType}`
							: item.type}"
					>
						<i class="fa-solid {item.icon} w-4 text-center text-surface-600-400"></i>
						<span class="font-medium">{item.label}</span>
						<i class="fa-solid fa-grip-vertical ml-auto text-[9px] text-surface-400-600"></i>
					</button>
				{/each}
			</div>
		{:else}
			<p class="text-[10px] text-surface-500">{m.noNodeTypeMatches()}</p>
		{/each}
		<p class="mt-3 text-[10px] leading-relaxed text-surface-500">
			{m.workflowBuilderHint()}
		</p>
	</div>

	<div class="mt-auto p-3 border-t border-surface-200-800">
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400 mb-2">
			{m.workflowVariables()}
		</h3>
		{#each variables as variable (variable.id)}
			<div class="flex items-center gap-1.5 py-1 text-xs group">
				<i class="fa-solid fa-cube text-[9px] text-surface-500"></i>
				<span class="font-mono text-surface-800-200 truncate">{variable.key}</span>
				<span class="badge preset-tonal text-[8px] px-1 py-0">{variable.type}</span>
				<button
					type="button"
					aria-label="Remove variable"
					class="ml-auto opacity-0 group-hover:opacity-100 text-error-500 hover:text-error-600 cursor-pointer text-[10px] transition-opacity"
					onclick={() => onRemoveVariable(variable.id)}
				>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</div>
		{/each}
		<form class="flex items-center gap-1 mt-2" onsubmit={submitVariable}>
			<input
				type="text"
				class="input text-xs px-1.5 py-1 min-w-0 flex-1"
				placeholder={m.variableKey()}
				bind:value={newVariableKey}
			/>
			<select class="select text-xs px-1 py-1 w-16" bind:value={newVariableType}>
				{#each VARIABLE_TYPES as t}
					<option value={t}>{t}</option>
				{/each}
			</select>
			<button
				type="submit"
				aria-label={m.addVariable()}
				class="btn-icon preset-tonal w-6 h-6 text-xs"
				disabled={!newVariableKey.trim()}
			>
				<i class="fa-solid fa-plus"></i>
			</button>
		</form>
	</div>

	<div class="p-3 border-t border-surface-200-800">
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400 mb-2">
			<i class="fa-solid fa-lock mr-1"></i>{m.workflowSecrets()}
		</h3>
		{#each secrets as secret (secret.id)}
			<div class="flex items-center gap-1.5 py-1 text-xs group">
				<i class="fa-solid fa-key text-[9px] text-surface-500"></i>
				<span class="font-mono text-surface-800-200 truncate">{secret.name}</span>
				<button
					type="button"
					aria-label="Remove secret"
					class="ml-auto opacity-0 group-hover:opacity-100 text-error-500 hover:text-error-600 cursor-pointer text-[10px] transition-opacity"
					onclick={() => onRemoveSecret(secret.id)}
				>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</div>
		{/each}
		<form class="flex items-center gap-1 mt-2" onsubmit={submitSecret}>
			<input
				type="text"
				class="input text-xs px-1.5 py-1 min-w-0 flex-1"
				placeholder={m.secretName()}
				bind:value={newSecretName}
			/>
			<input
				type="password"
				class="input text-xs px-1.5 py-1 min-w-0 flex-1"
				placeholder={m.secretValue()}
				bind:value={newSecretValue}
			/>
			<button
				type="submit"
				aria-label={m.addSecret()}
				class="btn-icon preset-tonal w-6 h-6 text-xs shrink-0"
				disabled={!newSecretName.trim() || !newSecretValue}
			>
				<i class="fa-solid fa-plus"></i>
			</button>
		</form>
	</div>
</aside>
