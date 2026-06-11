<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = 'default'
	}: Props = $props();

	const matrixHidden = context === 'fromBaseModel';
</script>

{#if !matrixHidden}
	<AutocompleteSelect
		{form}
		optionsEndpoint="pmbok/responsibility-matrices"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
		field="matrix"
		cacheLock={cacheLocks['matrix']}
		bind:cachedValue={formDataCache['matrix']}
		label={m.responsibilityMatrix()}
		disabled={!!initialData.matrix}
	/>
{/if}

<TextField
	{form}
	field="name"
	cacheLock={cacheLocks['name']}
	bind:cachedValue={formDataCache['name']}
	label={m.responsibilityActivity()}
/>

<TextArea
	{form}
	field="description"
	label={m.description()}
	cacheLock={cacheLocks['description']}
	bind:cachedValue={formDataCache['description']}
/>

<TextField
	type="number"
	{form}
	field="order"
	cacheLock={cacheLocks['order']}
	bind:cachedValue={formDataCache['order']}
	label={m.order()}
/>
