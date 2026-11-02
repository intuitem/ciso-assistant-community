<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '#lib/utils/types.js';
	import { m } from '#paraglide/messages.js';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="ttp-catalogs"
	field="catalog"
	cacheLock={cacheLocks['catalog']}
	bind:cachedValue={formDataCache['catalog']}
	label={m.ttpCatalog()}
	disabled={Boolean(object?.id)}
	helpText={object?.id ? m.threatModelCatalogLocked() : undefined}
/>
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	translateOptions={false}
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>
