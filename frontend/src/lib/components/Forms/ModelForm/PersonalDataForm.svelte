<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
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

<AutocompleteSelect
	{form}
	field="category"
	options={model.selectOptions['category']}
	cacheLock={cacheLocks['category']}
	bind:cachedValue={formDataCache['category']}
	label={m.category()}
/>

<TextField
	{form}
	field="retention"
	label={m.retention()}
	cacheLock={cacheLocks['retention']}
	bind:cachedValue={formDataCache['retention']}
/>
<AutocompleteSelect
	{form}
	field="deletion_policy"
	options={model.selectOptions['deletion_policy']}
	cacheLock={cacheLocks['deletion_policy']}
	bind:cachedValue={formDataCache['deletion_policy']}
	label={m.deletionPolicy()}
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

<Checkbox
	{form}
	field="is_sensitive"
	label={m.isSensitive()}
	cacheLock={cacheLocks['is_sensitive']}
	bind:cachedValue={formDataCache['is_sensitive']}
/>

<AutocompleteSelect
	{form}
	lazy
	field="assets"
	optionsEndpoint="assets"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type',
				translate: true
			}
		],
		classes: 'text-blue-500'
	}}
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
	label={m.assets()}
	multiple={true}
/>

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
	/>
	<MarkdownField
		{form}
		field="description"
		label={m.description()}
		cacheLock={cacheLocks['description']}
		bind:cachedValue={formDataCache['description']}
	/>
</Dropdown>
