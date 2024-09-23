<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
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

{#if model.urlModel === 'reference-controls'}
	<TextField
		{form}
		field="ref_id"
		label={m.ref()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
	/>
	<Select
		{form}
		options={model.selectOptions['category']}
		field="category"
		label={m.category()}
		cacheLock={cacheLocks['category']}
		bind:cachedValue={formDataCache['category']}
	/>
	<Select
		{form}
		options={model.selectOptions['csf_function']}
		field="csf_function"
		label={m.csfFunction()}
		cacheLock={cacheLocks['csf_function']}
		bind:cachedValue={formDataCache['csf_function']}
	/>
	<TextArea
		{form}
		field="annotation"
		label={m.annotation()}
		cacheLock={cacheLocks['annotation']}
		bind:cachedValue={formDataCache['annotation']}
	/>
	<TextField
		{form}
		field="provider"
		label={m.provider()}
		cacheLock={cacheLocks['provider']}
		bind:cachedValue={formDataCache['provider']}
	/>
	<AutocompleteSelect
		{form}
		options={getOptions({ objects: model.foreignKeys['folder'] })}
		field="folder"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		hidden={initialData.folder}
	/>
{/if}
