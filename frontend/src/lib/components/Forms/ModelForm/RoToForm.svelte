<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import * as m from '$paraglide/messages.js';
	import { getOptions } from '$lib/utils/crud';
	import TextArea from '../TextArea.svelte';
	import NumberField from '../NumberField.svelte';

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
	multiple
	{form}
	options={getOptions({
		objects: model.foreignKeys['feared_events'],
		extra_fields: [['folder', 'str']],
		label: 'auto'
	})}
	field="feared_events"
	label={m.fearedEvents()}
/>
<Select
	{form}
	options={model.selectOptions['risk-origin']}
	field="risk_origin"
	label={m.riskOrigin()}
	cacheLock={cacheLocks['risk_origin']}
	bind:cachedValue={formDataCache['risk_origin']}
/>
<TextArea
	{form}
	field="target_objective"
	label={m.targetObjective()}
	cacheLock={cacheLocks['target_objective']}
	bind:cachedValue={formDataCache['target_objective']}
/>
<Select
	{form}
	options={model.selectOptions['motivation']}
	field="motivation"
	label={m.motivation()}
	cacheLock={cacheLocks['motivation']}
	bind:cachedValue={formDataCache['motivation']}
/>
<Select
	{form}
	options={model.selectOptions['resources']}
	field="resources"
	label={m.resources()}
	cacheLock={cacheLocks['resources']}
	bind:cachedValue={formDataCache['resources']}
/>
<Select
	{form}
	options={model.selectOptions['pertinence']}
	field="pertinence"
	label={m.pertinence()}
	cacheLock={cacheLocks['pertinence']}
	bind:cachedValue={formDataCache['pertinence']}
/>
<NumberField
	{form}
	field="activity"
	label={m.activity()}
	cacheLock={cacheLocks['activity']}
	bind:cachedValue={formDataCache['activity']}
/>
<Checkbox {form} field="is_selected" label={m.isSelected()} />
<TextArea
	{form}
	field="justification"
	label={m.justification()}
	cacheLock={cacheLocks['justification']}
	bind:cachedValue={formDataCache['justification']}
/>
