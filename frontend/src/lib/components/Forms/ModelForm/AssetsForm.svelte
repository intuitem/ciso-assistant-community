<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
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
	export let object: any = {};
	export let data: any = {};
</script>

{#if model.urlModel === 'assets'}
	<TextArea
		{form}
		field="business_value"
		label={m.businessValue()}
		cacheLock={cacheLocks['business_value']}
		bind:cachedValue={formDataCache['business_value']}
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
	<Select
		{form}
		options={model.selectOptions['type']}
		field="type"
		label="Type"
		cacheLock={cacheLocks['type']}
		bind:cachedValue={formDataCache['type']}
	/>
	<AutocompleteSelect
		disabled={data.type === 'PR'}
		multiple
		{form}
		options={getOptions({ objects: model.foreignKeys['parent_assets'], self: object })}
		field="parent_assets"
		cacheLock={cacheLocks['parent_assets']}
		bind:cachedValue={formDataCache['parent_assets']}
		label={m.parentAssets()}
	/>
{/if}
