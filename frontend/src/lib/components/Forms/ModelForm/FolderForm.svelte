<script lang="ts">
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { CacheLock } from '$lib/utils/types';

	export let form: SuperValidated<any>;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	import * as m from '$paraglide/messages.js';
</script>

<TextField
	{form}
	field="ref_id"
	label={'reference id'}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
