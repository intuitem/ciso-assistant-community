<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import Score from '../Score.svelte';
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
	optionsEndpoint="entities"
	field="provider_entity"
	cacheLock={cacheLocks['provider_entity']}
	bind:cachedValue={formDataCache['provider_entity']}
	label={m.providerEntity()}
	hidden={initialData.provider_entity}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<Score
	{form}
	label={m.criticality()}
	field="criticality"
	inversedColors
	fullDonut
	min_score={1}
	max_score={4}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	field="assets"
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
	label={m.assets()}
/>
