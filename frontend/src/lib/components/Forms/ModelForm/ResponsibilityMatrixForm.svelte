<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import TextField from '../TextField.svelte';
	import Select from '../Select.svelte';
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
		context = 'default'
	}: Props = $props();
</script>

<TextField
	{form}
	field="ref_id"
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
	label={m.refId()}
/>

<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>

<Select
	{form}
	field="preset"
	options={[
		{ value: 'raci', label: 'RACI' },
		{ value: 'rasci', label: 'RASCI' },
		{ value: 'rapid', label: 'RAPID' }
	]}
	label={m.preset()}
	helpText={m.responsibilityMatrixPresetHelpText()}
	disableDoubleDash={true}
	disabled={!!object?.id}
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
