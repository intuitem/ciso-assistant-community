<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import HiddenInput from '../HiddenInput.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
</script>

<HiddenInput {form} field="requirement_assessments" />
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
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
	field="owners"
	cacheLock={cacheLocks['owners']}
	bind:cachedValue={formDataCache['owners']}
	label={m.owner()}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="approver"
	cacheLock={cacheLocks['approver']}
	bind:cachedValue={formDataCache['approver']}
	label={m.approver()}
/>
<Select
	{form}
	options={model.selectOptions['severity']}
	field="severity"
	label={m.severity()}
	cacheLock={cacheLocks['severity']}
	bind:cachedValue={formDataCache['severity']}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	disableDoubleDash="true"
	bind:cachedValue={formDataCache['status']}
/>
<TextField
	type="date"
	{form}
	field="expiration_date"
	label={m.expirationDate()}
	cacheLock={cacheLocks['expiration_date']}
	bind:cachedValue={formDataCache['expiration_date']}
/>
