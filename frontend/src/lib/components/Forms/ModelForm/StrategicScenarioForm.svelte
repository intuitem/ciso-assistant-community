<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperValidated } from 'sveltekit-superforms';
	import TextField from '../TextArea.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let context: string;
</script>

<p class="text-sm text-gray-500">{m.strategicScenarioHelpText()}</p>
{#if context !== 'edit'}
	<AutocompleteSelect
		{form}
		options={getOptions({ objects: model.foreignKeys['ro_to_couple'], label: 'str' })}
		field="ro_to_couple"
		cacheLock={cacheLocks['ro_to_couple']}
		bind:cachedValue={formDataCache['ro_to_couple']}
		label={m.roToCouple()}
		hidden={initialData.ro_to_couple}
	/>
{/if}
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
