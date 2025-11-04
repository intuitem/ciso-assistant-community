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
		data?: any;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		object = {}
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="metric-instances"
	optionsExtraFields={[['folder', 'str']]}
	field="metric_instance"
	cacheLock={cacheLocks['metric_instance']}
	bind:cachedValue={formDataCache['metric_instance']}
	label={m.metricInstance()}
/>
<TextField
	{form}
	type="datetime-local"
	field="timestamp"
	label={m.timestamp()}
	cacheLock={cacheLocks['timestamp']}
	bind:cachedValue={formDataCache['timestamp']}
	disabled={object.id}
/>
<TextArea
	{form}
	field="value"
	label={m.value()}
	helpText={'JSON format: {"result": 42.5}'}
	cacheLock={cacheLocks['value']}
	bind:cachedValue={formDataCache['value']}
/>
