<script lang="ts">
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { m } from '$paraglide/messages';

	let {
		integrationId,
		initialConfig = null,
		form,
		onSave = (config) => console.log('Saved:', config)
	} = $props();

	const LOCAL_FIELDS = [
		{ key: 'name', label: 'Name / Title', type: 'string', required: true },
		{ key: 'description', label: 'Description', type: 'text', required: false },
		{ key: 'eta', label: 'Due Date (ETA)', type: 'date', required: false },
		{ key: 'ref_id', label: 'Reference ID (External)', type: 'string', required: false },
		{
			key: 'status',
			label: 'Status',
			type: 'choice',
			choices: [
				{ value: 'to_do', label: 'To Do' },
				{ value: 'in_progress', label: 'In Progress' },
				{ value: 'on_hold', label: 'On Hold' },
				{ value: 'active', label: 'Active' },
				{ value: 'deprecated', label: 'Deprecated' }
			]
		},
		{
			key: 'priority',
			label: 'Priority',
			type: 'choice',
			choices: [
				{ value: 1, label: 'P1 - Critical' },
				{ value: 2, label: 'P2 - High' },
				{ value: 3, label: 'P3 - Medium' },
				{ value: 4, label: 'P4 - Low' }
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

	async function fetchRpc(action: string, params = {}) {
		try {
			const res = await fetch(`/settings/integrations/configs/${integrationId}/rpc`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action, params })
			});
			const data = await res.json();
			return data.result || [];
		} catch (e) {
			console.error(`RPC ${action} failed:`, e);
			return [];
		}
	}

	async function loadTables() {
		const rawTables = await fetchRpc('get_tables');
		// Transform to Autocomplete options format
		tables = rawTables.map((t: Record<string, any>) => ({
			value: t.name,
			label: `${t.label} [${t.name}]`
		}));
	}

	async function loadColumns(tableName: string) {
		if (!tableName) return;
		isLoadingColumns = true;
		const rawCols = await fetchRpc('get_columns', { table_name: tableName });

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

	function handleTableChange(val: string) {
		selectedTable = val;
		fieldMap = {}; // Clear mappings on table switch to avoid invalid references
		valueMap = {};
		columns = [];
		loadColumns(val);
	}

	function handleSave() {
		onSave({
			table_name: selectedTable,
			field_map: $state.snapshot(fieldMap),
			value_map: $state.snapshot(valueMap)
		});
	}
</script>

<div class="p-6 max-w-4xl mx-auto bg-white rounded-xl shadow-sm border border-surface-200">
	<div class="mb-8 border-b border-surface-100 pb-4">
		<h2 class="text-xl font-bold text-surface-800">ServiceNow Integration Setup</h2>
		<p class="text-sm text-surface-500 mt-1">Map your local controls to ServiceNow records.</p>
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
				helpText={m.serviceNowTableHelpText()}
				baseClass="w-full md:w-1/2"
			/>
		{/key}
	</section>

	{#if selectedTable}
		<section class="mb-8 animate-fade-in">
			<div class="flex justify-between items-center mb-4">
				<h3 class="text-lg font-semibold text-surface-700">Field Mapping</h3>
			</div>

			<div class="bg-surface-50 rounded-lg p-4 border border-surface-200">
				<div
					class="grid grid-cols-12 gap-4 mb-2 text-xs font-semibold text-surface-500 uppercase tracking-wider"
				>
					<div class="col-span-5">Local Field</div>
					<div class="col-span-1 text-center"></div>
					<div class="col-span-6">ServiceNow Column</div>
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

							<div class="col-span-1 text-center text-surface-300">→</div>

							<div class="col-span-6">
								{#key columns}
									<AutocompleteSelect
										{form}
										field={`map_${field.key}`}
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
				<h3 class="text-lg font-semibold text-surface-700 mb-4">Value Mapping</h3>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					{#each activeChoiceFields as field}
						{@const remoteField = fieldMap[field.key]}
						{@const choices = choicesCache[`${selectedTable}:${remoteField}`] || []}

						<div class="border border-surface-200 rounded-lg overflow-hidden">
							<div
								class="bg-surface-100 px-4 py-2 border-b border-surface-200 font-medium text-surface-700 flex justify-between"
							>
								<span>{field.label} Mapping</span>
								<span class="text-xs bg-surface-200 px-2 py-1 rounded text-surface-600">
									mapped to: {remoteField}
								</span>
							</div>

							<div class="p-4 bg-white space-y-3">
								{#each field.choices as choice}
									<div class="flex items-center justify-between gap-2">
										<div class="w-1/3 text-sm text-surface-600 truncate" title={choice.label}>
											{choice.label}
										</div>
										<div class="text-surface-300">→</div>

										<div class="w-2/3">
											{#key choices}
												<AutocompleteSelect
													{form}
													field={`val_map_${field.key}_${choice.value}`}
													options={choices}
													optionsValueField="value"
													optionsLabelField="label"
													cachedValue={(valueMap[field.key] ??= {})[choice.value]}
													onChange={(val) => ((valueMap[field.key] ??= {})[choice.value] = val)}
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

		<div class="flex justify-end pt-4 border-t border-surface-100">
			<button
				onclick={handleSave}
				class="bg-secondary-600 hover:bg-secondary-700 text-white font-medium py-2 px-6 rounded-md transition-colors shadow-sm"
			>
				Save Configuration
			</button>
		</div>
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
