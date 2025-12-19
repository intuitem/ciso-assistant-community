<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
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
		debug?: boolean;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		debug = false
	}: Props = $props();
</script>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="metric-definitions"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	field="metric_definition"
	cacheLock={cacheLocks['metric_definition']}
	bind:cachedValue={formDataCache['metric_definition']}
	label={m.metricDefinition()}
	disabled={!!initialData.metric_definition}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	disableDoubleDash
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<Select
	{form}
	options={model.selectOptions['collection_frequency']}
	field="collection_frequency"
	label={m.collectionFrequency()}
	cacheLock={cacheLocks['collection_frequency']}
	bind:cachedValue={formDataCache['collection_frequency']}
/>
<TextField
	{form}
	type="number"
	field="target_value"
	label={m.targetValue()}
	cacheLock={cacheLocks['target_value']}
	bind:cachedValue={formDataCache['target_value']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users"
	optionsLabelField="email"
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	label={m.owner()}
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
