<script lang="ts">
	import Select from '../Select.svelte';
    import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="incidents"
	field="incident"
	cacheLock={cacheLocks['incident']}
	bind:cachedValue={formDataCache['incident']}
	label={m.incident()}
	hidden={initialData.incident}
/>
<AutocompleteSelect
	required
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<TextField
	{form}
	field="entry"
	label={m.entry()}
	cacheLock={cacheLocks['entry']}
	bind:cachedValue={formDataCache['entry']}
	data-focusindex="0"
/>
<Select
    {form}
    options={model.selectOptions['entry_type']}
    field="entry_type"
    label={m.entryType()}
    cacheLock={cacheLocks['entry_type']}
    bind:cachedValue={formDataCache['entry_type']}
/>
<TextField
	type="date"
	{form}
	field="timestamp"
	label={m.timestamp()}
	cacheLock={cacheLocks['timestamp']}
	bind:cachedValue={formDataCache['timestamp']}
/>
<TextArea
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
<AutocompleteSelect
	{form}
    multiple
	optionsEndpoint="evidences"
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.evidences()}
/>
