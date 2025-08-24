<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
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
	options={model.selectOptions['attack_stage']}
	field="attack_stage"
	label={m.attackStage()}
	disableDoubleDash
	cacheLock={cacheLocks['attack_stage']}
	bind:cachedValue={formDataCache['attack_stage']}
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
	optionsEndpoint="threats"
	field="threat"
	cacheLock={cacheLocks['threat']}
	bind:cachedValue={formDataCache['threat']}
	label={m.threat()}
/>
<Select
	{form}
	options={model.selectOptions['icon']}
	field="icon"
	label={m.icon()}
	cacheLock={cacheLocks['icon']}
	bind:cachedValue={formDataCache['icon']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="operating-modes"
	field="operating_modes"
	cacheLock={cacheLocks['operating_modes']}
	bind:cachedValue={formDataCache['operating_modes']}
	label={m.operatingModes()}
	hidden
/>
