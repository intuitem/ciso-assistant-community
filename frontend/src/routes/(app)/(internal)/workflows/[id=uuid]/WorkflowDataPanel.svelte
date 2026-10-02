<script lang="ts">
	import { m } from '$paraglide/messages';
	import { VARIABLE_TYPES } from './builder-constants';
	import SecretInlineForm from './SecretInlineForm.svelte';
	import { formatVariableValue, parseVariableValue } from './variable-values';

	// The workflow-level data CRUD (variables + secrets), shared between the
	// Inspector's no-selection Workflow panel and the canvas "Variables" toggle
	// panel. Readonly (archived) views still list everything, minus the
	// add/remove controls.
	interface Props {
		variables: { id: string; key: string; type: string; default_value?: unknown }[];
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
		// The value every run starts with; null clears it.
		onUpdateVariableDefault?: (id: string, value: unknown) => void;
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
		onUpdateVariableDefault,
		onAddSecret,
		onRemoveSecret
	}: Props = $props();

	let newVariableKey = $state('');
	let newVariableType = $state('string');

	function submitVariable(event: Event) {
		event.preventDefault();
		const key = newVariableKey.trim();
		if (!key) return;
		onAddVariable?.(key, newVariableType);
		newVariableKey = '';
	}

	// Default editing keeps the typed text per variable only while it is not
	// the canonical text of a valid value (half-typed JSON, "1." in a number),
	// and writes the parsed value through as soon as it is valid. Template
	// reads stay pure; drafts change only in handlers and the effect below.
	let defaultDrafts = $state<Record<string, string>>({});

	function defaultText(variable: { id: string; default_value?: unknown }): string {
		return defaultDrafts[variable.id] ?? formatVariableValue(variable.default_value);
	}

	function defaultInvalid(variable: { id: string; type: string }) {
		const draft = defaultDrafts[variable.id];
		return draft !== undefined && !parseVariableValue(variable.type, draft).ok;
	}

	function editDefault(variable: { id: string; type: string }, raw: string) {
		const parsed = parseVariableValue(variable.type, raw);
		if (parsed.ok && formatVariableValue(parsed.value) === raw) {
			delete defaultDrafts[variable.id];
		} else {
			defaultDrafts[variable.id] = raw;
		}
		if (parsed.ok) onUpdateVariableDefault?.(variable.id, parsed.value);
	}

	// A change from elsewhere (undo, another panel) replaces the stored value:
	// drop the drafts that no longer describe it. Invalid drafts stay, they are
	// what the author is still typing.
	$effect(() => {
		for (const variable of variables) {
			const draft = defaultDrafts[variable.id];
			if (draft === undefined) continue;
			const parsed = parseVariableValue(variable.type, draft);
			if (
				parsed.ok &&
				formatVariableValue(parsed.value) !== formatVariableValue(variable.default_value)
			) {
				delete defaultDrafts[variable.id];
			}
		}
	});

	function inputType(type: string): string {
		if (type === 'number') return 'number';
		if (type === 'date') return 'date';
		return 'text';
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
				<div class="py-1 text-xs group" data-testid="variable-row">
					<div class="flex items-center gap-1.5">
						<i class="fa-solid fa-cube text-[9px] text-surface-500 shrink-0"></i>
						<span class="font-mono text-surface-800-200 truncate">{variable.key}</span>
						<span class="badge preset-tonal text-[8px] px-1 py-0 shrink-0">{variable.type}</span>
						<span class="ml-auto min-w-0 flex items-center gap-1.5">
							{#if variable.key in referenceVariables}
								<span
									class="font-mono text-[9px] text-surface-500 truncate"
									title={m.variableLastRunValue()}
								>
									{formatVariableValue(referenceVariables[variable.key])}
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
					<!-- The default, on its own line: the panel is narrow and the key
					     line is already full. -->
					<div class="flex items-center gap-1.5 pl-4 mt-0.5">
						<span class="text-[9px] uppercase tracking-wide text-surface-500 shrink-0"
							>{m.variableDefault()}</span
						>
						{#if readonly}
							<span class="font-mono text-[10px] text-surface-700-300 truncate">
								{formatVariableValue(variable.default_value) || '—'}
							</span>
						{:else if variable.type === 'boolean'}
							<select
								class="select text-[10px] font-mono h-6 py-0 pl-1.5 pr-6 w-auto"
								value={defaultText(variable)}
								onchange={(e) => editDefault(variable, e.currentTarget.value)}
								data-testid="variable-default-{variable.key}"
							>
								<option value="">{m.variableDefaultNone()}</option>
								<option value="true">true</option>
								<option value="false">false</option>
							</select>
						{:else}
							<input
								type={inputType(variable.type)}
								class="input text-[10px] font-mono h-6 py-0 px-1.5 flex-1 min-w-0 {defaultInvalid(
									variable
								)
									? 'border-error-500'
									: ''}"
								placeholder={m.variableDefaultNone()}
								value={defaultText(variable)}
								oninput={(e) => editDefault(variable, e.currentTarget.value)}
								aria-invalid={defaultInvalid(variable)}
								title={defaultInvalid(variable)
									? m.variableValueInvalid({ key: variable.key })
									: m.variableDefaultHint()}
								data-testid="variable-default-{variable.key}"
							/>
						{/if}
					</div>
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
					{#each VARIABLE_TYPES as t (t)}
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
			<SecretInlineForm onAdd={(name, value) => onAddSecret?.(name, value)} formClass="mt-2" />
		{/if}
	</div>
</div>
