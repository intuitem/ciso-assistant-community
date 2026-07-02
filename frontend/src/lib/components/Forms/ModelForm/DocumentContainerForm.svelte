<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
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

	const documentTypeOptions = [
		{ label: m.policy(), value: 'policy' },
		{ label: m.procedure(), value: 'procedure' },
		{ label: m.charter(), value: 'charter' },
		{ label: m.record(), value: 'record' },
		{ label: m.meetingMinutes(), value: 'meeting_minutes' },
		{ label: m.other(), value: 'other' }
	];
</script>

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
