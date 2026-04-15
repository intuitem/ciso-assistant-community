<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
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

<FolderTreeSelect
	{form}
	writable="add_vulnerability"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>

<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>

<Select
	{form}
	options={model.selectOptions['severity']}
	field="severity"
	label={m.severity()}
	cacheLock={cacheLocks['severity']}
	bind:cachedValue={formDataCache['severity']}
/>
<AutocompleteSelect
	multiple
	lazy
	{form}
	optionsEndpoint="assets"
	optionsLabelField="auto"
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
	label={m.assets()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="applied_controls"
	label={m.appliedControls()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="security-exceptions"
	optionsExtraFields={[['folder', 'str']]}
	field="security_exceptions"
	cacheLock={cacheLocks['security_exceptions']}
	bind:cachedValue={formDataCache['security_exceptions']}
	label={m.securityExceptions()}
/>
<AutocompleteSelect
	multiple
	lazy
	{form}
	optionsEndpoint="security-advisories"
	optionsInfoFields={{
		fields: [{ field: 'ref_id' }],
		classes: 'text-blue-500'
	}}
	field="security_advisories"
	label={m.securityAdvisories()}
/>
<AutocompleteSelect
	multiple
	lazy
	{form}
	optionsEndpoint="cwes"
	optionsInfoFields={{
		fields: [{ field: 'ref_id' }],
		classes: 'text-blue-500'
	}}
	field="cwes"
	label={m.cwes()}
/>
<TextField
	type="date"
	{form}
	field="detected_at"
	label={m.detectedAt()}
	helpText={m.detectedAtHelpText()}
	cacheLock={cacheLocks['detected_at']}
	bind:cachedValue={formDataCache['detected_at']}
/>
<TextField
	type="date"
	{form}
	field="eta"
	label={m.eta()}
	cacheLock={cacheLocks['eta']}
	bind:cachedValue={formDataCache['eta']}
/>
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	translateOptions={false}
	optionsLabelField="label"
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>
