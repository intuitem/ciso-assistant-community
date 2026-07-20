<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Checkbox from '../Checkbox.svelte';
	import ListSelector from '../ListSelector.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		shape?: any;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		shape = {},
		context
	}: Props = $props();
</script>

<ListSelector
	{form}
	field="permissions"
	label={m.permissions()}
	optionsEndpoint="service-accounts/permissions"
	optionsLabelField="normalized_codename"
	groupBy={[{ field: 'content_type', path: ['app_label'] }, { field: 'normalized_model' }]}
	cacheLock={cacheLocks['permissions']}
	bind:cachedValue={formDataCache['permissions']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="folders"
	field="perimeter_folders"
	cacheLock={cacheLocks['perimeter_folders']}
	bind:cachedValue={formDataCache['perimeter_folders']}
	label={m.domains()}
/>
<Checkbox
	{form}
	field="is_recursive"
	label={m.isRecursive()}
	helpText={m.isRecursiveHelpText()}
	cacheLock={cacheLocks['is_recursive']}
	bind:cachedValue={formDataCache['is_recursive']}
/>
