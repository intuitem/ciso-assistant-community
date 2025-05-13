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
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
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
	optionsEndpoint="qualifications"
	field="qualifications"
	label={m.qualifications()}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="assets"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
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
</Dropdown>
