<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
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

<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['folder'] })}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
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
	options={[
		{ label: '--', value: -1 },
		{ label: 'Low', value: 0 },
		{ label: 'Medium', value: 1 },
		{ label: 'High', value: 2 },
		{ label: 'Critical', value: 3 }
	]}
	field="severity"
	label={'Severity'}
	cacheLock={cacheLocks['severity']}
	bind:cachedValue={formDataCache['severity']}
/>

<TextField
	{form}
	field="ref_id"
	label={'Ref ID'}
	helpText={'Ref ID help text'}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<TextField
	{form}
	field="reference_ref_id"
	label={'Reference Ref ID'}
	helpText={'Reference Ref ID help text'}
	cacheLock={cacheLocks['reference_ref_id']}
	bind:cachedValue={formDataCache['reference_ref_id']}
/>

<Select
	{form}
	disabled={!formDataCache['reference_ref_id']}
	options={[
		{ label: '--', value: '' },
		{ label: 'CVE', value: 'cve' },
		{ label: 'KEV', value: 'kev' }
	]}
	field="vulnerability_catalog"
	label={'Reference vulnerability catalog'}
	cacheLock={cacheLocks['vulnerability_catalog']}
	bind:cachedValue={formDataCache['vulnerability_catalog']}
/>
