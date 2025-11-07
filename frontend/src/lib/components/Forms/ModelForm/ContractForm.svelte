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
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {}
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	field="folder"
	optionsEndpoint="folders"
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
	field="status"
	optionsEndpoint="contracts/status"
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	label={m.status()}
/>
<TextField
	type="date"
	{form}
	field="start_date"
	label={m.startDate()}
	cacheLock={cacheLocks['start_date']}
	bind:cachedValue={formDataCache['start_date']}
/>
<TextField
	type="date"
	{form}
	field="end_date"
	label={m.endDate()}
	cacheLock={cacheLocks['end_date']}
	bind:cachedValue={formDataCache['end_date']}
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
	optionsEndpoint="entities"
	field="entities"
	cacheLock={cacheLocks['entities']}
	bind:cachedValue={formDataCache['entities']}
	label={m.entities()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="solutions"
	optionsExtraFields={[['provider_entity', 'str']]}
	field="solutions"
	cacheLock={cacheLocks['solutions']}
	bind:cachedValue={formDataCache['solutions']}
	label={m.solutions()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="evidences"
	optionsExtraFields={[['folder', 'str']]}
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.evidences()}
/>
<AutocompleteSelect
	{form}
	multiple
	field="filtering_labels"
	optionsEndpoint="filtering-labels"
	cacheLock={cacheLocks['filtering_labels']}
	bind:cachedValue={formDataCache['filtering_labels']}
	label={m.filteringLabels()}
/>
