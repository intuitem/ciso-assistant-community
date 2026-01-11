<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: any;
		object?: any;
		debug?: boolean;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		object = {},
		debug = false
	}: Props = $props();

	const { value: valueFieldProxy } = formFieldProxy(form, 'value');

	// Access metric definition from multiple sources:
	// 1. formDataCache (when selecting in autocomplete with includeAllOptionFields)
	// 2. data.metric_instance (when editing existing sample)
	// 3. initialData._metric_definition (when pre-filled from parent metric-instance page)
	const metricInstanceCache = $derived(
		Array.isArray(formDataCache['metric_instance'])
			? formDataCache['metric_instance'][0]
			: formDataCache['metric_instance']
	);

	const metricDefinition = $derived(
		metricInstanceCache?.metric_definition ||
			data?.metric_instance?.metric_definition ||
			initialData?._metric_definition
	);
	const isQualitative = $derived(metricDefinition?.category === 'qualitative');
	const unitName = $derived(metricDefinition?.unit?.name || '');

	// Build choices for select dropdown
	const choiceOptions = $derived.by(() => {
		if (!isQualitative || !metricDefinition?.choices_definition) return [];

		return metricDefinition.choices_definition.map((choice: any, index: number) => ({
			label: `${index + 1}. ${choice.name}`,
			value: (index + 1).toString() // Store 1-based indices
		}));
	});

	// Parse initial value for qualitative metrics
	const selectedChoiceIndex = $derived.by(() => {
		if (!isQualitative) return '';
		try {
			const parsed =
				typeof $valueFieldProxy === 'string' ? JSON.parse($valueFieldProxy) : $valueFieldProxy;
			return parsed?.choice_index?.toString() || '';
		} catch {
			return '';
		}
	});

	function handleQualitativeChange(selectedIndex: string) {
		$valueFieldProxy = JSON.stringify({ choice_index: parseInt(selectedIndex) });
	}

	// For quantitative metrics, parse the numeric value
	const quantitativeValue = $derived.by(() => {
		if (isQualitative) return '';
		try {
			const parsed =
				typeof $valueFieldProxy === 'string' ? JSON.parse($valueFieldProxy) : $valueFieldProxy;
			return parsed?.result?.toString() || '';
		} catch {
			return '';
		}
	});

	function handleQuantitativeChange(event: Event) {
		const value = (event.target as HTMLInputElement).value;
		const numValue = parseFloat(value);
		if (!isNaN(numValue)) {
			$valueFieldProxy = JSON.stringify({ result: numValue });
		}
	}

	// Get current datetime for max attribute (prevent future timestamps)
	const maxTimestamp = $derived(() => {
		const now = new Date();
		now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
		return now.toISOString().slice(0, 16);
	});
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="metric-instances"
	optionsExtraFields={[
		['folder', 'str'],
		['metric_definition', 'fk']
	]}
	field="metric_instance"
	cacheLock={cacheLocks['metric_instance']}
	bind:cachedValue={formDataCache['metric_instance']}
	includeAllOptionFields={true}
	label={m.metricInstance()}
	hidden={!!initialData.metric_instance}
	disabled={!!initialData.metric_instance}
/>
<TextField
	{form}
	type="datetime-local"
	field="timestamp"
	label={m.timestamp()}
	cacheLock={cacheLocks['timestamp']}
	bind:cachedValue={formDataCache['timestamp']}
	disabled={object.id}
	max={maxTimestamp()}
/>

{#if debug}
	<!-- Debug section -->
	<div class="card bg-yellow-50 p-4 my-4 border-2 border-yellow-300">
		<h4 class="font-semibold mb-2">Debug Info:</h4>
		<div class="text-xs space-y-2">
			<div>
				<strong>initialData.metric_instance:</strong>
				{initialData.metric_instance || 'null'}
			</div>
			<div>
				<strong>initialData._metric_definition:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(
						initialData._metric_definition,
						null,
						2
					)}</pre>
			</div>
			<div>
				<strong>metricInstanceCache:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(metricInstanceCache, null, 2)}</pre>
			</div>
			<div>
				<strong>metricDefinition (resolved):</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(metricDefinition, null, 2)}</pre>
			</div>
			<div>
				<strong>isQualitative:</strong>
				{isQualitative}
			</div>
			<div>
				<strong>choiceOptions:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(choiceOptions, null, 2)}</pre>
			</div>
		</div>
	</div>
{/if}

{#if isQualitative}
	<div class="form-group">
		<label for="value-select" class="text-sm font-semibold block mb-2">{m.value()}</label>
		<select
			id="value-select"
			class="select w-full"
			value={selectedChoiceIndex}
			onchange={(e) => handleQualitativeChange(e.currentTarget.value)}
		>
			<option value="">-- {m.select()} --</option>
			{#each choiceOptions as option}
				<option value={option.value}>{option.label}</option>
			{/each}
		</select>
	</div>
{:else}
	<div class="form-group">
		<label for="value-input" class="text-sm font-semibold block mb-2">
			{m.value()}
			{#if unitName}
				<span class="text-gray-500 font-normal">({unitName})</span>
			{/if}
		</label>
		<input
			id="value-input"
			type="number"
			step="any"
			class="input w-full"
			value={quantitativeValue}
			oninput={handleQuantitativeChange}
		/>
	</div>
{/if}
