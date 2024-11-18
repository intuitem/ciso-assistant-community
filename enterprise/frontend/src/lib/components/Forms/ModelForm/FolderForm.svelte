<script lang="ts">
	import { getOptions } from '$lib/utils/crud';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperValidated } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
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
	options={getOptions({ objects: model.foreignKeys['parent_folder'] })}
	field="parent_folder"
	cacheLock={cacheLocks['parent_folder']}
	bind:cachedValue={formDataCache['parent_folder']}
	label={m.parentDomain()}
	hide={initialData.parent_folder}
/>
