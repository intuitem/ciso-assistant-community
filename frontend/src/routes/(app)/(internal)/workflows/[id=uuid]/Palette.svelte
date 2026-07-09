<script lang="ts">
	import { m } from '$paraglide/messages';

	interface Variable {
		id: string;
		key: string;
		type: string;
	}

	interface Props {
		hasStart: boolean;
		variables: Variable[];
		onAdd: (nodeType: string) => void;
		onAddVariable: (key: string, type: string) => void;
		onRemoveVariable: (id: string) => void;
	}

	let { hasStart, variables, onAdd, onAddVariable, onRemoveVariable }: Props = $props();

	const PALETTE = $derived([
		...(hasStart
			? []
			: [{ type: 'start', icon: 'fa-play', label: m.workflowNodeStart() }]),
		{ type: 'task', icon: 'fa-clipboard-check', label: m.workflowNodeTask() },
		{ type: 'condition', icon: 'fa-code-branch', label: m.workflowNodeCondition() },
		{ type: 'action', icon: 'fa-bolt', label: m.workflowNodeAction() },
		{ type: 'subprocess', icon: 'fa-diagram-project', label: m.workflowNodeSubprocess() },
		{ type: 'end', icon: 'fa-flag-checkered', label: m.workflowNodeEnd() }
	]);

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

	function handleDragStart(event: DragEvent, nodeType: string) {
		event.dataTransfer?.setData('application/ciso-workflow-node', nodeType);
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
		<div class="flex flex-col gap-1.5">
			{#each PALETTE as item (item.type)}
				<button
					type="button"
					draggable="true"
					ondragstart={(e) => handleDragStart(e, item.type)}
					onclick={() => onAdd(item.type)}
					class="flex items-center gap-2 px-2.5 py-2 rounded-base border border-surface-200-800 bg-surface-50-950 text-xs text-surface-800-200 cursor-grab hover:border-primary-400 hover:shadow-sm transition-all text-left"
					data-testid="palette-{item.type}"
				>
					<i class="fa-solid {item.icon} w-4 text-center text-surface-600-400"></i>
					<span class="font-medium">{item.label}</span>
					<i class="fa-solid fa-grip-vertical ml-auto text-[9px] text-surface-400-600"></i>
				</button>
			{/each}
		</div>
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
</aside>
