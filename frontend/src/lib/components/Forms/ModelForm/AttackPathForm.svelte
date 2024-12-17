<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperValidated } from 'sveltekit-superforms';
	import Checkbox from '../Checkbox.svelte';
	import TextArea from '../TextArea.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let context: 'create' | 'edit' = 'create';
</script>

<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['ro_to_couple'], label: 'str' })}
	field="ro_to_couple"
	cacheLock={cacheLocks['ro_to_couple']}
	bind:cachedValue={formDataCache['ro_to_couple']}
	label={m.roToCouple()}
	hidden={initialData.ro_to_couple}
/>
<AutocompleteSelect
	{form}
	multiple
	options={getOptions({
		objects: model.foreignKeys['stakeholders'],
		label: 'str'
	})}
	field="stakeholders"
	cacheLock={cacheLocks['stakeholders']}
	bind:cachedValue={formDataCache['stakeholders']}
	label={m.stakeholders()}
/>

<Checkbox {form} field="is_selected" label={m.selected()} />
<TextArea
	{form}
	field="justification"
	label={m.justification()}
	cacheLock={cacheLocks['justification']}
	bind:cachedValue={formDataCache['justification']}
/>
