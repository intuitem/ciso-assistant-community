<script lang="ts">
	import Checkbox from '../Checkbox.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { formFieldProxy } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
	}

	let { form, cacheLocks = {}, formDataCache = $bindable({}) }: Props = $props();

	const { value: hexcolor } = formFieldProxy(form, 'hexcolor');
</script>

<label class="label">
	<span class="text-sm font-semibold">{m.color()}</span>
	<div class="flex items-center gap-2">
		<input type="color" bind:value={$hexcolor} class="h-10 w-16 cursor-pointer rounded" />
		<input type="text" bind:value={$hexcolor} class="input w-28" placeholder="#RRGGBB" />
	</div>
</label>
<Checkbox
	{form}
	field="is_visible"
	label={m.isVisible()}
	helpText={m.tierIsVisibleHelpText()}
	cacheLock={cacheLocks['is_visible']}
	bind:cachedValue={formDataCache['is_visible']}
/>
