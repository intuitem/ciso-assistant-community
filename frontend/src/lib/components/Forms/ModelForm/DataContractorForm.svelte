<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

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

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<AutocompleteSelect
	{form}
	field="relationship_type"
	options={model.selectOptions['relationship_type']}
	cacheLock={cacheLocks['relationship_type']}
	bind:cachedValue={formDataCache['relationship_type']}
	label={m.relationshipType()}
/>
<AutocompleteSelect
	{form}
	field="country"
	options={model.selectOptions['country']}
	cacheLock={cacheLocks['country']}
	bind:cachedValue={formDataCache['country']}
	label={m.country()}
/>
<TextField
	{form}
	field="documentation_link"
	label={m.documentationLink()}
	cacheLock={cacheLocks['documentation_link']}
	bind:cachedValue={formDataCache['documentation_link']}
/>
<AutocompleteSelect
	{form}
	field="entity"
	optionsEndpoint="entities"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
/>
<AutocompleteSelect
	{form}
	field="processing"
	optionsEndpoint="processings"
	cacheLock={cacheLocks['processing']}
	bind:cachedValue={formDataCache['processing']}
	label={m.processing()}
	hidden={initialData.processing}
/>
