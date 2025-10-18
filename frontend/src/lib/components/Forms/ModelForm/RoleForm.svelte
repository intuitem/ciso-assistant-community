<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import ListSelector from '../ListSelector.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		updated_fields?: Set<string>;
		context?: 'create' | 'edit';
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		updated_fields = new Set(),
		context = 'edit'
	}: Props = $props();
</script>

{#if context === 'edit'}
	<ListSelector
		{form}
		field="permissions"
		label={m.permissions()}
		optionsEndpoint="permissions"
		optionsLabelField="normalized_codename"
		groupBy={[{ field: 'content_type', path: ['app_label'] }, { field: 'normalized_model' }]}
		cacheLock={cacheLocks['permissions']}
		bind:cachedValue={formDataCache['permissions']}
	/>
{/if}
