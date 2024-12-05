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
	options={getOptions({ objects: model.foreignKeys['ro_to_couple'] })}
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
		objects: model.foreignKeys['threats'],
		extra_fields: [['folder', 'str']],
		label: 'auto'
	})}
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>
<Select
	{form}
	options={model.selectOptions['likelihood']}
	field="likelihood"
	label={m.likelihood()}
	cacheLock={cacheLocks['likelihood']}
	bind:cachedValue={formDataCache['likelihood']}
/>
