<script lang="ts">
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
	}

	let { form, cacheLocks = {}, formDataCache = $bindable({}) }: Props = $props();
</script>

<TextField
	{form}
	field="label"
	label={m.label()}
	cacheLock={cacheLocks['label']}
	bind:cachedValue={formDataCache['label']}
/>
