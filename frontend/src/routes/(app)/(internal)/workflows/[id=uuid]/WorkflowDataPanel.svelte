<script lang="ts">
	import { m } from '$paraglide/messages';

	// The workflow-level data CRUD (variables + secrets), shared between the
	// Inspector's no-selection Workflow panel and the canvas "Variables" toggle
	// panel. Readonly (archived) views still list everything, minus the
	// add/remove controls.
	interface Props {
		variables: { id: string; key: string; type: string }[];
		secrets?: { id: string; name: string }[];
		referenceVariables?: Record<string, unknown>;
		readonly?: boolean;
		// Wide surfaces (the bottom toggle panel) show variables and secrets
		// side by side so neither hides below the fold; narrow ones (the
		// Inspector empty state) stack them.
		columns?: boolean;
		// Returns the created variable's id (or the existing one's on a
		// duplicate key), so callers can select it right away.
		onAddVariable?: (key: string, type: string) => string | null;
		onRemoveVariable?: (id: string) => void;
		onAddSecret?: (name: string, value: string) => void;
		onRemoveSecret?: (id: string) => void;
	}

	let {
		variables,
		secrets = [],
		referenceVariables = {},
		readonly = false,
		columns = false,
		onAddVariable,
		onRemoveVariable,
		onAddSecret,
		onRemoveSecret
	}: Props = $props();

	const VARIABLE_TYPES = ['string', 'number', 'boolean', 'date', 'json'];

	let newVariableKey = $state('');
	let newVariableType = $state('string');

	function submitVariable(event: Event) {
		event.preventDefault();
		const key = newVariableKey.trim();
		if (!key) return;
		onAddVariable?.(key, newVariableType);
		newVariableKey = '';
	}

	let newSecretName = $state('');
	let newSecretValue = $state('');

	function submitSecret(event: Event) {
		event.preventDefault();
		const name = newSecretName.trim();
		if (!name || !newSecretValue) return;
		onAddSecret?.(name, newSecretValue);
		newSecretName = '';
		newSecretValue = '';
	}

	function formatReferenceValue(value: unknown): string {
		return typeof value === 'string' ? value : JSON.stringify(value);
	}
</script>

<div
	class={columns ? 'grid grid-cols-2 gap-x-8 gap-y-4 items-start' : 'space-y-4'}
	data-testid="workflow-data-panel"
>
	<div>
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400 mb-1">
			{m.workflowVariables()}
		</h3>
		<div class="max-h-56 overflow-y-auto">
			{#each variables as variable (variable.id)}
				<div class="flex items-center gap-1.5 py-1 text-xs group">
					<i class="fa-solid fa-cube text-[9px] text-surface-500 shrink-0"></i>
					<span class="font-mono text-surface-800-200 truncate">{variable.key}</span>
					<span class="badge preset-tonal text-[8px] px-1 py-0 shrink-0">{variable.type}</span>
					<span class="ml-auto min-w-0 flex items-center gap-1.5">
						{#if variable.key in referenceVariables}
							<span
								class="font-mono text-[9px] text-surface-500 truncate"
								title={formatReferenceValue(referenceVariables[variable.key])}
							>
								{formatReferenceValue(referenceVariables[variable.key])}
							</span>
						{/if}
						{#if !readonly}
							<button
								type="button"
								aria-label="Remove variable"
								class="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-error-500 hover:text-error-600 cursor-pointer text-[10px] transition-opacity shrink-0"
								onclick={() => onRemoveVariable?.(variable.id)}
							>
								<i class="fa-solid fa-xmark"></i>
							</button>
						{/if}
					</span>
				</div>
			{/each}
		</div>
		{#if !readonly}
			<form class="flex items-center gap-1 mt-2" autocomplete="off" onsubmit={submitVariable}>
				<input
					type="text"
					class="input text-xs px-1.5 py-1 min-w-0 flex-1"
					placeholder={m.variableKey()}
					autocomplete="off"
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
		{/if}
	</div>

	<div class={columns ? '' : 'pt-2 border-t border-surface-200-800'}>
		<h3 class="text-xs font-semibold uppercase tracking-wide text-surface-600-400 mb-1">
			<i class="fa-solid fa-lock mr-1"></i>{m.workflowSecrets()}
		</h3>
		<div class="max-h-40 overflow-y-auto">
			{#each secrets as secret (secret.id)}
				<div class="flex items-center gap-1.5 py-1 text-xs group">
					<i class="fa-solid fa-key text-[9px] text-surface-500 shrink-0"></i>
					<span class="font-mono text-surface-800-200 truncate">{secret.name}</span>
					{#if !readonly}
						<button
							type="button"
							aria-label="Remove secret"
							class="ml-auto opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-error-500 hover:text-error-600 cursor-pointer text-[10px] transition-opacity"
							onclick={() => onRemoveSecret?.(secret.id)}
						>
							<i class="fa-solid fa-xmark"></i>
						</button>
					{/if}
				</div>
			{/each}
		</div>
		{#if !readonly}
			<form class="flex items-center gap-1 mt-2" autocomplete="off" onsubmit={submitSecret}>
				<input
					type="text"
					class="input text-xs px-1.5 py-1 min-w-0 flex-1"
					placeholder={m.secretName()}
					autocomplete="off"
					bind:value={newSecretName}
				/>
				<input
					type="password"
					class="input text-xs px-1.5 py-1 min-w-0 flex-1"
					placeholder={m.secretValue()}
					autocomplete="new-password"
					data-1p-ignore
					data-lpignore="true"
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
		{/if}
	</div>
</div>
