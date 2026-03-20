<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		debug?: boolean;
	}

	let {
		form,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		debug = false
	}: Props = $props();
</script>

{#if debug}
	<!-- Debug section -->
	<div class="card bg-yellow-50 p-4 my-4 border-2 border-yellow-300">
		<h4 class="font-semibold mb-2">Debug Info:</h4>
		<div class="text-xs space-y-2">
			<div>
				<strong>initialData:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(initialData, null, 2)}</pre>
			</div>
			<div>
				<strong>formDataCache:</strong>
				<pre class="bg-white p-2 rounded mt-1">{JSON.stringify(formDataCache, null, 2)}</pre>
			</div>
		</div>
	</div>
{/if}

<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	field="filtering_labels"
	cacheLock={cacheLocks['filtering_labels']}
	bind:cachedValue={formDataCache['filtering_labels']}
	label={m.labels()}
/>
