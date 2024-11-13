<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
</script>

<TextField
	{form}
	field="label"
	label={m.label()}
	cacheLock={cacheLocks['label']}
	bind:cachedValue={formDataCache['label']}
/>
