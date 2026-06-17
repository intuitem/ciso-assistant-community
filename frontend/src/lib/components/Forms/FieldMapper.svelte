<script lang="ts">
	import { onMount } from 'svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	const toastStore = getToastStore();

	let {
		integrationId,
		initialConfig = null,
		form,
		title = m.integrationMappingsTitle(),
		description = m.integrationMappingsHelpText(),
		remoteFieldLabel = m.remoteField(),
		tableHelpText = m.integrationTableHelpText(),
		onSave = (config) => console.log('Saved:', config),
		// Fires after handleTableChange so the parent page can sync field_map /
		// value_map into the superform store. Without this, the per-row
		// AutocompleteSelect rebinds happen on the next tick but the form's
		// settings.field_map / settings.value_map keep stale values.
		onMapsChange = (_maps: { field_map: Record<string, any>; value_map: Record<string, any> }) =>
			undefined
	} = $props();

	const LOCAL_FIELDS = [
		{ key: 'name', label: m.name(), type: 'string', required: true },
		{ key: 'description', label: m.description(), type: 'text', required: false },
		{ key: 'eta', label: m.eta(), type: 'date', required: false },
		{ key: 'ref_id', label: m.refId(), type: 'string', required: false },
		{
			key: 'status',
			label: m.status(),
			type: 'choice',
			choices: [
				{ value: 'to_do', label: m.toDo() },
				{ value: 'in_progress', label: m.inProgress() },
				{ value: 'on_hold', label: m.onHold() },
				{ value: 'active', label: m.active() },
				{ value: 'degraded', label: m.degraded() },
				{ value: 'deprecated', label: m.deprecated() }
			]
		},
		{
			key: 'priority',
			label: m.priority(),
			type: 'choice',
			choices: [
				{ value: 1, label: m.p1() },
				{ value: 2, label: m.p2() },
				{ value: 3, label: m.p3() },
				{ value: 4, label: m.p4() }
			]
		}
	];

	let selectedTable = $state(initialConfig?.table_name || '');
	let fieldMap = $state(initialConfig?.field_map || {});
	let valueMap = $state(initialConfig?.value_map || {});

	// Data sourced from RPC
	let tables = $state([]);
	let columns = $state([]);
	let choicesCache = $state({}); // Key: "table:field", Value: Option[]
	let isLoadingColumns = $state(false);

	let activeChoiceFields = $derived(
		LOCAL_FIELDS.filter((f) => f.type === 'choice' && fieldMap[f.key])
	);

	// Returns `null` (not `[]`) on failure so callers can branch on it.
	// Surfaces a toast for non-2xx and network/parse errors so the user has a
	// signal when the integration backend is unreachable or the action isn't
	// supported. Callers that want a "safe empty" should do `?? []` themselves.
	async function fetchRpc(action: string, params = {}): Promise<any> {
		let res: Response;
		try {
			res = await fetch(`/settings/integrations/configs/${integrationId}/rpc`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action, params })
			});
		} catch (e) {
			console.error(`RPC ${action} network error:`, e);
			toastStore.trigger({
				message: `Could not reach the integration backend (${action}).`,
				preset: 'error'
			});
			return null;
		}

		let data: any = null;
		try {
			data = await res.json();
		} catch {
			// Non-JSON body (e.g. Django debug HTML on 500). Fall through.
		}

		if (!res.ok) {
			const detail = (data && (data.error || data.message)) || `HTTP ${res.status}`;
			console.error(`RPC ${action} failed:`, detail, data);
			toastStore.trigger({
				message: `Integration action "${action}" failed: ${detail}`,
				preset: 'error'
			});
			return null;
		}

		return data?.result ?? null;
	}

	async function loadTables() {
		const rawTables = (await fetchRpc('get_tables')) ?? [];
		// Transform to Autocomplete options format
		tables = rawTables.map((t: Record<string, any>) => ({
			value: t.name,
			label: `${t.label} [${t.name}]`
		}));
	}

	async function loadColumns(tableName: string) {
		if (!tableName) return;
		isLoadingColumns = true;
		const rawCols = (await fetchRpc('get_columns', { table_name: tableName })) ?? [];

		columns = rawCols.map((c: Record<string, any>) => ({
			value: c.name,
			label: c.label,
			// We can pass extra info to help filtering or UI
			infoString: { string: c.readonly ? '(Read Only)' : c.name, position: 'suffix' },
			original: c // Keep ref for choice logic
		}));
		isLoadingColumns = false;
	}

	async function loadChoices(tableName: string, fieldName: string) {
		const cacheKey = `${tableName}:${fieldName}`;
		if (choicesCache[cacheKey]) return; // Dedup

		const rawChoices = await fetchRpc('get_choices', {
			table_name: tableName,
			field_name: fieldName
		});
		if (rawChoices === null) return; // RPC failed — don't cache an empty list as success
		choicesCache[cacheKey] = rawChoices.map((c) => ({ value: c.value, label: c.label }));
	}

	onMount(() => {
		if (integrationId) loadTables();
		if (selectedTable) loadColumns(selectedTable);
	});

	// Trigger loadChoices when a choice field is mapped
	$effect(() => {
		activeChoiceFields.forEach((f) => {
			const remoteField = fieldMap[f.key];
			if (remoteField && selectedTable) {
				// Only fetch if we haven't already
				loadChoices(selectedTable, remoteField);
			}
		});
	});

	// Seed an empty per-field map up-front so the template can read
	// `valueMap[field.key][choice.value]` without mutating state during render.
	$effect(() => {
		for (const f of activeChoiceFields) {
			if (!valueMap[f.key]) valueMap[f.key] = {};
		}
	});

	async function handleTableChange(val: string) {
		// Snapshot the user's current maps before touching anything. We need
		// them as a fallback when the provider has no defaults to suggest
		// (e.g. ServiceNow) — without the snapshot, a table change would
		// silently wipe rows the user just finished configuring.
		const prevFieldMap = { ...fieldMap };
		const prevValueMap = { ...valueMap };

		selectedTable = val;
		columns = [];
		await loadColumns(val);
		if (!val) {
			fieldMap = {};
			valueMap = {};
			onMapsChange({ field_map: {}, value_map: {} });
			return;
		}

		const suggested = await fetchRpc('suggest_mapping', { table_name: val });
		const nextFieldMap = (suggested?.field_map as Record<string, any>) ?? {};
		const nextValueMap = (suggested?.value_map as Record<string, any>) ?? {};
		const hasSuggestion =
			Object.keys(nextFieldMap).length > 0 || Object.keys(nextValueMap).length > 0;

		// Providers with real defaults (Jira) win: clear and replace. Providers
		// with the BaseFieldMapper no-op (ServiceNow) keep the user's prior
		// mappings so a table change doesn't destroy hand-configured rows.
		const finalFieldMap = hasSuggestion ? nextFieldMap : prevFieldMap;
		const finalValueMap = hasSuggestion ? nextValueMap : prevValueMap;

		// Pre-load every choice list the value_map references BEFORE we surface
		// the maps. Otherwise the value-mapping AutocompleteSelects mount with
		// empty options, optionsLoaded=false, and their post-mount $effect is
		// gated off so the selected option never gets set.
		await Promise.all(
			Object.keys(finalValueMap).map(async (localField) => {
				const remoteField = finalFieldMap[localField];
				if (remoteField) await loadChoices(val, remoteField);
			})
		);

		fieldMap = finalFieldMap;
		valueMap = finalValueMap;
		onMapsChange({ field_map: finalFieldMap, value_map: finalValueMap });
	}
</script>

<div class="p-6 max-w-4xl mx-auto bg-white rounded-xl shadow-sm border border-surface-200">
	<div class="mb-8 border-b border-surface-100 pb-4">
		<h2 class="text-xl font-bold text-surface-800">
			{title}
		</h2>
		<p class="text-sm text-surface-500 mt-1">{description}</p>
	</div>

	<section class="mb-8">
		{#key tables}
			<AutocompleteSelect
				{form}
				field="table_name"
				valuePath="settings.table_name"
				label={m.targetTable()}
				optionsValueField="value"
				optionsLabelField="label"
				options={tables}
				cachedValue={selectedTable}
				onChange={handleTableChange}
				helpText={tableHelpText}
				baseClass="w-full md:w-1/2"
			/>
		{/key}
	</section>

	{#if selectedTable}
		<section class="mb-8 animate-fade-in">
			<div class="flex justify-between items-center mb-4">
				<h3 class="text-lg font-semibold text-surface-700">{m.fieldMapping()}</h3>
			</div>

			<div class="bg-surface-50 rounded-lg p-4 border border-surface-200">
				<div
					class="grid grid-cols-12 gap-4 mb-2 text-xs font-semibold text-surface-500 uppercase tracking-wider"
				>
					<div class="col-span-5">{m.localField()}</div>
					<div class="col-span-1 text-center"></div>
					<div class="col-span-6">{remoteFieldLabel}</div>
				</div>

				<div class="space-y-4">
					{#each LOCAL_FIELDS as field}
						<div class="grid grid-cols-12 gap-4 items-center">
							<div class="col-span-5">
								<div class="font-medium text-surface-700">
									{field.label}
									{#if field.required}<span class="text-error-400">*</span>{/if}
								</div>
								<div class="text-xs text-surface-400 font-mono">{field.key}</div>
							</div>

							<div class="col-span-1 text-center text-surface-300">↔</div>

							<div class="col-span-6">
								{#key columns}
									<AutocompleteSelect
										{form}
										field={field.key}
										valuePath={`settings.field_map.${field.key}`}
										options={columns}
										cachedValue={fieldMap[field.key]}
										onChange={(val) => (fieldMap[field.key] = val)}
										nullable={true}
										baseClass="w-full"
									/>
								{/key}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</section>

		{#if activeChoiceFields.length > 0}
			<section class="mb-8 animate-fade-in">
				<h3 class="text-lg font-semibold text-surface-700 mb-4">{m.valueMapping()}</h3>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					{#each activeChoiceFields as field}
						{@const remoteField = fieldMap[field.key]}
						{@const choices = choicesCache[`${selectedTable}:${remoteField}`] || []}

						<div class="border border-surface-200 rounded-lg">
							<div
								class="bg-surface-100 px-4 py-2 border-b border-surface-200 font-medium text-surface-700 flex justify-between rounded-t-lg"
							>
								<span>{m.valueMappingForField({ field: safeTranslate(field.label) })}</span>
								<span class="text-xs bg-surface-200 px-2 py-1 rounded text-surface-600">
									{m.valueMappingToField({ field: remoteField })}
								</span>
							</div>

							<div class="p-4 bg-white space-y-3">
								{#each field.choices as choice}
									<div class="flex items-center justify-between gap-2">
										<div class="w-1/3 text-sm text-surface-600 truncate" title={choice.label}>
											{choice.label}
										</div>
										<div class="text-surface-300">↔</div>

										<div class="w-2/3">
											{#key choices}
												<AutocompleteSelect
													{form}
													field={String(choice.value)}
													valuePath={`settings.value_map.${field.key}.${choice.value}`}
													options={choices}
													optionsValueField="value"
													optionsLabelField="label"
													cachedValue={valueMap[field.key]?.[choice.value]}
													onChange={(val) => {
														valueMap[field.key] ??= {};
														valueMap[field.key][choice.value] = val;
													}}
													nullable={true}
													baseClass="w-full"
												/>
											{/key}
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</div>

<style>
	.animate-fade-in {
		animation: fadeIn 0.3s ease-in-out;
	}
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
