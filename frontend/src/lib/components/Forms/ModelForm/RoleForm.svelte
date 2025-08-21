<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		updated_fields?: Set<string>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		updated_fields = new Set()
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="permissions"
	optionsInfoFields={{
		fields: [
			{
				field: 'content_type'
			}
		]
	}}
	field="permissions"
	cacheLock={cacheLocks['permissions']}
	bind:cachedValue={formDataCache['permissions']}
	label={m.permissions()}
/>
