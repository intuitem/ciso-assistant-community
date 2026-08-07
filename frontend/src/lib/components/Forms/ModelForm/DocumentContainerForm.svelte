<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '../TextField.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	import { DOCUMENT_TYPES } from '$lib/utils/documentTypes';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = ''
	}: Props = $props();

	const documentTypeOptions = DOCUMENT_TYPES.map((t) => ({
		label: t.label(),
		value: t.key
	}));
</script>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<Select
	{form}
	options={documentTypeOptions}
	field="document_type"
	label={m.documentType()}
	cacheLock={cacheLocks['document_type']}
	bind:cachedValue={formDataCache['document_type']}
/>

<AutocompleteSelect
	{form}
	multiple
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	translateOptions={false}
	allowUserOptions="append"
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="classification-levels"
	optionsLabelField="label"
	field="classification"
	label={m.classification()}
	nullable
	cacheLock={cacheLocks['classification']}
	bind:cachedValue={formDataCache['classification']}
/>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-link"
	header={m.relationships()}
>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="policies"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="policies"
		label={m.policies()}
		cacheLock={cacheLocks['policies']}
		bind:cachedValue={formDataCache['policies']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="applied-controls"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="applied_controls"
		label={m.appliedControls()}
		cacheLock={cacheLocks['applied_controls']}
		bind:cachedValue={formDataCache['applied_controls']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="task-templates"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="task_templates"
		label={m.taskTemplates()}
		cacheLock={cacheLocks['task_templates']}
		bind:cachedValue={formDataCache['task_templates']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="processings"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="processings"
		label={m.processings()}
		cacheLock={cacheLocks['processings']}
		bind:cachedValue={formDataCache['processings']}
	/>
</Dropdown>
