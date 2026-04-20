<script lang="ts">
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
	}

	let { form, model, cacheLocks = {}, formDataCache = $bindable({}) }: Props = $props();
</script>

<Checkbox
	{form}
	field="is_active"
	label={m.isActive()}
	cacheLock={cacheLocks['is_active']}
	bind:cachedValue={formDataCache['is_active']}
/>
