<script lang="ts">
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';

	export let form: SuperValidated<any>;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
</script>

<TextField
	{form}
	field="label"
	label={m.label()}
	cacheLock={cacheLocks['label']}
	bind:cachedValue={formDataCache['label']}
/>
