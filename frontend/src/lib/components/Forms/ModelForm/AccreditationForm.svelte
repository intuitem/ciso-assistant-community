<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
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
</script>

<TextField
	{form}
	field="ref_id"
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
	label={m.refId()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	pathField="path"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="author"
	cacheLock={cacheLocks['author']}
	bind:cachedValue={formDataCache['author']}
	nullable={true}
	label={m.author()}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="terminologies?field_path=accreditation.category&is_visible=true"
	optionsLabelField="translated_name"
	field="category"
	label={m.category()}
	cacheLock={cacheLocks['category']}
	bind:cachedValue={formDataCache['category']}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="compliance-assessments"
	optionsLabelField="auto"
	optionsExtraFields={[['perimeter', 'str']]}
	field="checklist"
	cacheLock={cacheLocks['checklist']}
	bind:cachedValue={formDataCache['checklist']}
	nullable={true}
	label={m.checklist()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="terminologies?field_path=accreditation.status&is_visible=true"
	optionsLabelField="translated_name"
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="generic-collections"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	field="linked_collection"
	cacheLock={cacheLocks['linked_collection']}
	bind:cachedValue={formDataCache['linked_collection']}
	nullable={true}
	label={m.linkedCollection()}
/>

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<AutocompleteSelect
		{form}
		optionsEndpoint="entities?relationship__name=accreditation_authority"
		field="authority"
		cacheLock={cacheLocks['authority']}
		bind:cachedValue={formDataCache['authority']}
		nullable={true}
		label={m.authority()}
		helpText={m.regulatoryAuthorityHelpText()}
	/>
	<TextField
		type="date"
		{form}
		field="expiry_date"
		cacheLock={cacheLocks['expiry_date']}
		bind:cachedValue={formDataCache['expiry_date']}
		label={m.expiryDate()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		createFromSelection={true}
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		field="filtering_labels"
		helpText={m.labelsHelpText()}
		label={m.labels()}
		translateOptions={false}
		allowUserOptions="append"
	/>
	<TextArea
		{form}
		field="observation"
		label={m.observation()}
		helpText={m.observationHelpText()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
</Dropdown>
