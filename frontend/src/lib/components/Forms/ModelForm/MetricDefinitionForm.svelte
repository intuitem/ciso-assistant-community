<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '#lib/components/Forms/TextField.svelte';
	import TextArea from '#lib/components/Forms/TextArea.svelte';
	import NumberField from '#lib/components/Forms/NumberField.svelte';
	import SegmentedControl from '../SegmentedControl.svelte';
	import Select from '../Select.svelte';
	import { directionOf, higherIsBetterFor, type Direction } from '#lib/utils/metrics.js';
	import OrderedEntryList from '#lib/components/OrderedEntryList.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '#lib/utils/types.js';
	import { m } from '#paraglide/messages.js';
	import { formFieldProxy } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: any;
		object?: Record<string, unknown>;
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

	const isQualitative = $derived.by(() => {
		return data?.category === 'qualitative';
	});

	// Direction is three-way: higher is better, lower is better, none
	// (informational). Stored as the nullable boolean.
	const { value: higherIsBetterValue } = formFieldProxy(form, 'higher_is_better');
	let direction = $state<Direction>(directionOf({ higher_is_better: $higherIsBetterValue }));
	const directionOptions = $derived([
		{ value: 'none', label: m.noDirection() },
		{ value: 'higher', label: m.higherIsBetter() },
		{ value: 'lower', label: m.lowerIsBetter() }
	]);
	function setDirection(value: string) {
		direction = value as Direction;
		$higherIsBetterValue = higherIsBetterFor(direction);
	}

	// Handle choices_definition as parsed array
	const { value: choicesDefinitionValue } = formFieldProxy(form, 'choices_definition');

	let choicesEntries = $state<Array<{ ref_id: string; name: string }>>([]);

	// Parse initial value
	$effect(() => {
		if ($choicesDefinitionValue) {
			try {
				if (typeof $choicesDefinitionValue === 'string') {
					choicesEntries = JSON.parse($choicesDefinitionValue);
				} else if (Array.isArray($choicesDefinitionValue)) {
					choicesEntries = $choicesDefinitionValue;
				}
			} catch (e) {
				console.error('Failed to parse choices_definition:', e);
				choicesEntries = [];
			}
		} else {
			choicesEntries = [];
		}
	});

	function handleChoicesChange(entries: Array<{ ref_id: string; name: string }>) {
		$choicesDefinitionValue = entries;
	}

	// Derived metric: the formula block, shared with the formula drawer of a
	// metric whose formula is its definition's.
	import DefinitionFormulaEditor, {
		type FormulaPreview
	} from '#lib/components/Metrology/DefinitionFormulaEditor.svelte';
	import { untrack } from 'svelte';

	const { value: datasetsValue } = formFieldProxy(form, 'datasets');
	const { value: inputsValue } = formFieldProxy(form, 'inputs');
	const { value: expressionValue } = formFieldProxy(form, 'expression');
	let formulaOpen = $state(false);
	// v1 creates computed metrics from metric instances (the compose modal):
	// the formula block only shows to edit a definition that already has one,
	// such as a formula over objects or one shipped in a library.
	const editsFormula = untrack(() => {
		const datasets = $datasetsValue;
		return (
			Boolean(($expressionValue as string | undefined)?.trim()) ||
			(Array.isArray($inputsValue) && $inputsValue.length > 0) ||
			(!!datasets && typeof datasets === 'object' && Object.keys(datasets).length > 0)
		);
	});
	$effect(() => {
		if ($datasetsValue && typeof $datasetsValue === 'object' && Object.keys($datasetsValue).length)
			formulaOpen = true;
		if (Array.isArray($inputsValue) && $inputsValue.length) formulaOpen = true;
		if ($expressionValue) formulaOpen = true;
	});
	let preview = $state<FormulaPreview | null>(null);
	function clearFormula() {
		$datasetsValue = null;
		$inputsValue = null;
		$expressionValue = '';
		preview = null;
	}
</script>

<Select
	{form}
	options={model.selectOptions['category']}
	field="category"
	label={m.category()}
	cacheLock={cacheLocks['category']}
	disableDoubleDash
	bind:cachedValue={formDataCache['category']}
/>
{#if isQualitative}
	<div class="form-group">
		<span class="text-sm font-semibold mb-2 block">{m.choicesDefinition()}</span>
		<OrderedEntryList bind:entries={choicesEntries} onchange={handleChoicesChange} />
	</div>
{:else}
	<AutocompleteSelect
		{form}
		optionsEndpoint="terminologies?field_path=metric_definition.unit&is_visible=true"
		optionsLabelField="translated_name"
		field="unit"
		label={m.unit()}
		cacheLock={cacheLocks['unit']}
		bind:cachedValue={formDataCache['unit']}
	/>
	<div class="grid grid-cols-[minmax(0,1fr)_8rem] gap-4">
		<TextField
			{form}
			type="number"
			field="default_target"
			label={m.defaultTarget()}
			helpText={m.defaultTargetHelpText()}
			cacheLock={cacheLocks['default_target']}
			bind:cachedValue={formDataCache['default_target']}
		/>
		<NumberField
			{form}
			field="decimals"
			label={m.decimals()}
			min={0}
			max={6}
			helpText={m.decimalsHelpText()}
			cacheLock={cacheLocks['decimals']}
			bind:cachedValue={formDataCache['decimals']}
		/>
	</div>
{/if}
<Select
	{form}
	options={model.selectOptions['default_collection_frequency']}
	field="default_collection_frequency"
	label={m.defaultCollectionFrequency()}
	helpText={m.defaultCollectionFrequencyHelpText()}
	cacheLock={cacheLocks['default_collection_frequency']}
	bind:cachedValue={formDataCache['default_collection_frequency']}
/>
<TextField
	{form}
	field="provider"
	label={m.provider()}
	cacheLock={cacheLocks['provider']}
	bind:cachedValue={formDataCache['provider']}
/>
<div class="form-group">
	<span class="text-sm font-semibold block mb-1">{m.direction()}</span>
	<SegmentedControl
		options={directionOptions}
		value={direction}
		onChange={setDirection}
		ariaLabel={m.direction()}
	/>
	<p class="text-xs text-surface-500 mt-1">
		{direction === 'none'
			? m.noDirectionHelpText()
			: direction === 'lower'
				? m.lowerIsBetterHelpText()
				: m.higherIsBetterHelpText()}
	</p>
</div>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	field="filtering_labels"
	cacheLock={cacheLocks['filtering_labels']}
	bind:cachedValue={formDataCache['filtering_labels']}
	label={m.labels()}
/>

{#if editsFormula}
	<div class="form-group rounded-base border border-surface-200-800 p-3 flex flex-col gap-2">
		<label class="flex items-center gap-2 text-sm font-semibold cursor-pointer">
			<input
				type="checkbox"
				class="checkbox"
				checked={formulaOpen}
				onchange={(e) => {
					formulaOpen = e.currentTarget.checked;
					if (!formulaOpen) clearFormula();
				}}
				data-testid="derived-metric-toggle"
			/>
			{m.derivedMetric()}
		</label>
		<p class="text-xs text-surface-500">{m.derivedMetricHelpText()}</p>
		{#if formulaOpen}
			<DefinitionFormulaEditor
				{form}
				definition={object}
				category={data?.category}
				choicesDefinition={data?.choices_definition}
				active={formulaOpen}
				bind:preview
			/>
		{/if}
	</div>
{/if}
