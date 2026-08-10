<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
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
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		object = {}
	}: Props = $props();

	const { value: valueFieldProxy } = formFieldProxy(form, 'value');

	// Get full metric instance data from autocomplete cache (includes nested fields like metric_definition, evidences)
	const metricInstanceCache = $derived.by(() => {
		const options = formDataCache['metric_instance_options'];
		if (options && Array.isArray(options) && options.length > 0) {
			return options[0];
		}
		return null;
	});

	const metricDefinition = $derived(
		metricInstanceCache?.metric_definition ||
			object?.metric_instance?.metric_definition ||
			data?.metric_instance?.metric_definition ||
			initialData?._metric_definition
	);
	const isQualitative = $derived(metricDefinition?.category === 'qualitative');
	const unitName = $derived(metricDefinition?.unit?.name || '');

	// Get evidence ID from metric instance for filtering evidence revisions
	const evidenceId = $derived.by(() => {
		if (metricInstanceCache?.evidences?.id) {
			return metricInstanceCache.evidences.id;
		}
		if (object?.metric_instance && typeof object.metric_instance === 'object') {
			return object.metric_instance?.evidences?.id;
		}
		if (data?.metric_instance?.evidences?.id) {
			return data.metric_instance.evidences.id;
		}
		if (initialData?._evidences?.id) {
			return initialData._evidences.id;
		}
		return null;
	});

	const hasEvidence = $derived(!!evidenceId);

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
	optionsEndpoint="metric-instances"
	optionsExtraFields={[
		['folder', 'str'],
		['metric_definition', 'fk'],
		['evidences', 'fk']
	]}
	field="metric_instance"
	cacheLock={cacheLocks['metric_instance']}
	bind:cachedValue={formDataCache['metric_instance']}
	bind:cachedOptions={formDataCache['metric_instance_options']}
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
				<span class="text-surface-600-400 font-normal">({unitName})</span>
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

<MarkdownField
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
	rows={4}
	defaultMode="edit"
/>

{#if hasEvidence}
	<AutocompleteSelect
		{form}
		optionsEndpoint={`evidence-revisions?evidence=${evidenceId}`}
		optionsLabelField="str"
		field="evidence_revision"
		cacheLock={cacheLocks['evidence_revision']}
		bind:cachedValue={formDataCache['evidence_revision']}
		label={m.evidenceRevision()}
	/>
{/if}
