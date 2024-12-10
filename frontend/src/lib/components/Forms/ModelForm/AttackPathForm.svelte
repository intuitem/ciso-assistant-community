<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import * as m from '$paraglide/messages.js';
	import { getOptions } from '$lib/utils/crud';
	import TextArea from '../TextArea.svelte';
	import NumberField from '../NumberField.svelte';
	import Checkbox from '../Checkbox.svelte';

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
