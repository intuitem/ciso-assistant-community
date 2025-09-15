<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';

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
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="assigned_to"
	cacheLock={cacheLocks['assigned_to']}
	bind:cachedValue={formDataCache['assigned_to']}
	label={m.assignedTo()}
/>
<Select
	{form}
	disableDoubleDash
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="organisation-issues"
	field="issues"
	optionsExtraFields={[['folder', 'str']]}
	cacheLock={cacheLocks['issues']}
	bind:cachedValue={formDataCache['issues']}
	label={m.organisationIssues()}
/>
<TextField
	type="date"
	{form}
	field="eta"
	label={m.eta()}
	helpText={m.etaHelpText()}
	cacheLock={cacheLocks['eta']}
	bind:cachedValue={formDataCache['eta']}
/>
<Dropdown open={false} class="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Select
		{form}
		options={model.selectOptions['health']}
		field="health"
		label={m.health()}
		helpText={m.healthFieldHelpText()}
		cacheLock={cacheLocks['health']}
		bind:cachedValue={formDataCache['health']}
	/>

	<TextField
		type="date"
		{form}
		field="due_date"
		label={m.dueDate()}
		helpText={m.dueDateHelpText()}
		cacheLock={cacheLocks['due_date']}
		bind:cachedValue={formDataCache['due_date']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="assets"
		optionsExtraFields={[['folder', 'str']]}
		optionsInfoFields={{
			fields: [
				{
					field: 'type'
				}
			],
			classes: 'text-blue-500'
		}}
		field="assets"
		cacheLock={cacheLocks['assets']}
		bind:cachedValue={formDataCache['assets']}
		label={m.assets()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="task-templates"
		field="tasks"
		optionsExtraFields={[['folder', 'str']]}
		cacheLock={cacheLocks['tasks']}
		bind:cachedValue={formDataCache['tasks']}
		label={m.taskTemplates()}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		helpText={m.observationHelpText()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
</Dropdown>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
