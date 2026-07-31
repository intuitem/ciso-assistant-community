<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

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

<Select
	{form}
	options={model.selectOptions['type']}
	field="type"
	label={m.type()}
	cacheLock={cacheLocks['type']}
	bind:cachedValue={formDataCache['type']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="threat-catalogs"
	field="catalog"
	label={m.threatCatalog()}
	cacheLock={cacheLocks['catalog']}
	bind:cachedValue={formDataCache['catalog']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="threats"
	field="parent"
	label={m.parentThreat()}
	cacheLock={cacheLocks['parent']}
	bind:cachedValue={formDataCache['parent']}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="reference-controls"
	field="reference_controls"
	label={m.referenceControls()}
	cacheLock={cacheLocks['reference_controls']}
	bind:cachedValue={formDataCache['reference_controls']}
/>
<MarkdownField
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
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	field="filtering_labels"
	translateOptions={false}
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>
