<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import OrderedEntryList from '$lib/components/OrderedEntryList.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { formFieldProxy } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {}
	}: Props = $props();

	const isQualitative = $derived.by(() => {
		return data?.category === 'qualitative';
	});

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
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
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
		<label class="text-sm font-semibold mb-2 block">{m.choicesDefinition()}</label>
		<OrderedEntryList bind:entries={choicesEntries} onchange={handleChoicesChange} />
	</div>
{:else}
	<TextField
		{form}
		field="unit"
		label={m.unit()}
		cacheLock={cacheLocks['unit']}
		bind:cachedValue={formDataCache['unit']}
	/>
	<TextField
		{form}
		type="number"
		field="min_value"
		label={m.minValue()}
		cacheLock={cacheLocks['min_value']}
		bind:cachedValue={formDataCache['min_value']}
	/>
	<TextField
		{form}
		type="number"
		field="max_value"
		label={m.maxValue()}
		cacheLock={cacheLocks['max_value']}
		bind:cachedValue={formDataCache['max_value']}
	/>
{/if}
<TextField
	{form}
	field="provider"
	label={m.provider()}
	cacheLock={cacheLocks['provider']}
	bind:cachedValue={formDataCache['provider']}
/>
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
