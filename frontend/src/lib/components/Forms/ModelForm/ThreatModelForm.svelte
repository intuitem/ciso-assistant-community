<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
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
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
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
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<TextField
	{form}
	field="name"
	label={m.name()}
	cacheLock={cacheLocks['name']}
	bind:cachedValue={formDataCache['name']}
/>
<TextArea
	{form}
	field="description"
	label={m.description()}
	cacheLock={cacheLocks['description']}
	bind:cachedValue={formDataCache['description']}
/>
