<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import CustomFieldsSection from '../CustomFieldsSection.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { formFieldProxy } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	const { value: folderId } = formFieldProxy(form, 'folder');
</script>

<Select
	{form}
	options={model.selectOptions?.['kind'] ?? []}
	field="kind"
	label={m.kind()}
	cacheLock={cacheLocks['kind']}
	bind:cachedValue={formDataCache['kind']}
	disableDoubleDash={true}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="actors?user__is_third_party=False"
	optionsLabelField="str"
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	nullable={true}
	label={m.owner()}
	helpText={m.projectOwnerHelpText()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="terminologies?field_path=project.status&is_visible=true"
	optionsLabelField="translated_name"
	field="status"
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	nullable={true}
	label={m.status()}
/>

<CustomFieldsSection {form} model="pmbok.project" folderId={$folderId} />

{#if !object?.id}
	<Checkbox
		{form}
		field="create_collection"
		label={m.createCollection()}
		helpText={m.createCollectionHelpText()}
		cacheLock={cacheLocks['create_collection']}
		bind:cachedValue={formDataCache['create_collection']}
	/>
{/if}
