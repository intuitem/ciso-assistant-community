<script lang="ts">
    import type { SuperValidated } from 'sveltekit-superforms';
    import type { ModelInfo, CacheLock } from '$lib/utils/types';
    import TextField from '$lib/components/Forms/TextField.svelte';
    import Select from '$lib/components/Forms/Select.svelte';
    import * as m from '$paraglide/messages.js';
	import TextArea from '../TextArea.svelte';

    export let form: SuperValidated<any>;
    export let model: ModelInfo;
    export let cacheLocks: Record<string, CacheLock> = {};
    export let formDataCache: Record<string, any> = {};
    export let initialData: Record<string, any> = {};
</script>

<TextField
	{form}
	field="version"
	label={m.version()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
<TextArea
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
<!-- <Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/> -->