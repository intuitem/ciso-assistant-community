<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import * as m from '$paraglide/messages.js';
	import { getOptions } from '$lib/utils/crud';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
</script>

<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['ebios_rm_study'] })}
	field="ebios_rm_study"
	cacheLock={cacheLocks['ebios_rm_study']}
	bind:cachedValue={formDataCache['ebios_rm_study']}
	label={m.ebiosRmStudy()}
	hidden={initialData.ebios_rm_study}
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
<AutocompleteSelect
	multiple
	{form}
	options={getOptions({
		objects: model.foreignKeys['attack_paths'],
		label: 'str'
	})}
	field="attack_paths"
	label={m.attackPaths()}
/>
<Select
	{form}
	options={model.selectOptions['likelihood']}
	field="likelihood"
	label={m.likelihood()}
	cacheLock={cacheLocks['likelihood']}
	bind:cachedValue={formDataCache['likelihood']}
/>
<Checkbox {form} field="is_selected" label={m.isSelected()} />
<TextArea
	{form}
	field="justification"
	label={m.justification()}
	cacheLock={cacheLocks['justification']}
	bind:cachedValue={formDataCache['justification']}
/>
