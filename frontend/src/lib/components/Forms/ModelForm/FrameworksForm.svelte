<script lang="ts">
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
</script>

{#if model.urlModel === 'frameworks'}
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
{/if}
