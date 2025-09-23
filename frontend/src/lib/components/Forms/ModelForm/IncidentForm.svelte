<script lang="ts">
	import Select from '../Select.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import * as m from '$paraglide/messages.js';

	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		schema?: any;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		schema = {},
		initialData = {}
	}: Props = $props();
	const disableDoubleDash = true;

	let currentDateTime = new Date(new Date().getTime() - new Date().getTimezoneOffset() * 60000)
		.toISOString()
		.slice(0, 19);
</script>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<TextField
	type="datetime-local"
	step="1"
	{form}
	field="reported_at"
	label={m.reportedAt()}
	value={currentDateTime}
	cacheLock={cacheLocks['reported_at']}
	bind:cachedValue={formDataCache['reported_at']}
/>

<Select
	{form}
	{disableDoubleDash}
	field="detection"
	label={m.detectedBy()}
	options={model.selectOptions['detection']}
	cacheLock={cacheLocks['detection']}
	bind:cachedValue={formDataCache['detection']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<Select
	{form}
	{disableDoubleDash}
	field="status"
	label={m.status()}
	options={model.selectOptions['status']}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<Select
	{form}
	{disableDoubleDash}
	options={[
		{ label: m.unknown(), value: 6 },
		{ label: m.critical(), value: 1 },
		{ label: m.major(), value: 2 },
		{ label: m.moderate(), value: 3 },
		{ label: m.minor(), value: 4 },
		{ label: m.low(), value: 5 }
	]}
	field="severity"
	label={m.severity()}
	cacheLock={cacheLocks['severity']}
	bind:cachedValue={formDataCache['severity']}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="terminologies?field_path=qualifications&is_visible=true"
	field="qualifications"
	optionsLabelField="translated_name"
	label={m.qualifications()}
/>
<TextField
	{form}
	field="link"
	label={m.link()}
	helpText={m.linkHelpText()}
	cacheLock={cacheLocks['link']}
	bind:cachedValue={formDataCache['link']}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<AutocompleteSelect
		multiple
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
		{form}
		multiple
		optionsEndpoint="threats"
		field="threats"
		cacheLock={cacheLocks['threats']}
		bind:cachedValue={formDataCache['threats']}
		label={m.threats()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="users?is_third_party=false"
		optionsLabelField="email"
		field="owners"
		cacheLock={cacheLocks['owners']}
		bind:cachedValue={formDataCache['owners']}
		label={m.owners()}
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
</Dropdown>
