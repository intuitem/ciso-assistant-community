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
	import { page } from '$app/stores';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let context: string;

	const activityBackground = context === 'edit' ? 'bg-white' : 'bg-surface-100-800-token';

	let activeActivity: string | null = null;
	$page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		} else if (key === 'activity' && value === 'three') {
			activeActivity = 'three';
		}
	});
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
<div
	class="relative p-2 space-y-2 rounded-md {activeActivity === 'one'
		? 'border-2 border-primary-500'
		: 'border-2 border-gray-300 border-dashed'}"
>
	<p
		class="absolute -top-3 {activityBackground} font-bold {activeActivity === 'one'
			? 'text-primary-500'
			: 'text-gray-500'}"
	>
		{m.activityOne()}
	</p>
	<Select
		{form}
		options={model.selectOptions['risk-origin']}
		field="risk_origin"
		label={m.riskOrigin()}
		cacheLock={cacheLocks['risk_origin']}
		bind:cachedValue={formDataCache['risk_origin']}
		helpText={m.riskOriginHelpText()}
	/>
	<TextArea
		{form}
		field="target_objective"
		label={m.targetObjective()}
		cacheLock={cacheLocks['target_objective']}
		bind:cachedValue={formDataCache['target_objective']}
		helpText={m.targetObjectiveHelpText()}
	/>
</div>
<div
	class="relative p-2 space-y-2 rounded-md {activeActivity === 'two'
		? 'border-2 border-primary-500'
		: 'border-2 border-gray-300 border-dashed'}"
>
	<p
		class="absolute -top-3 {activityBackground} font-bold {activeActivity === 'two'
			? 'text-primary-500'
			: 'text-gray-500'}"
	>
		{m.activityTwo()}
	</p>
	<Select
		{form}
		options={model.selectOptions['motivation']}
		field="motivation"
		label={m.motivation()}
		cacheLock={cacheLocks['motivation']}
		bind:cachedValue={formDataCache['motivation']}
		helpText={m.motivationHelpText()}
	/>
	<Select
		{form}
		options={model.selectOptions['resources']}
		field="resources"
		label={m.resources()}
		cacheLock={cacheLocks['resources']}
		bind:cachedValue={formDataCache['resources']}
		helpText={m.resourcesHelpText()}
	/>
	<Select
		{form}
		options={model.selectOptions['activity']}
		field="activity"
		label={m.activity()}
		cacheLock={cacheLocks['activity']}
		bind:cachedValue={formDataCache['activity']}
		helpText={m.activityHelpText()}
	/>
</div>
<div
	class="relative p-2 space-y-2 rounded-md {activeActivity === 'three'
		? 'border-2 border-primary-500'
		: 'border-2 border-gray-300 border-dashed'}"
>
	<p
		class="absolute -top-3 {activityBackground} font-bold {activeActivity === 'three'
			? 'text-primary-500'
			: 'text-gray-500'}"
	>
		{m.activityThree()}
	</p>
	<Checkbox
		{form}
		field="is_selected"
		label={m.isSelected()}
		helpText={m.roToIsSelectedHelpText()}
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
		helpText={m.roToFearedEventHelpText()}
	/>
	<TextArea
		{form}
		field="justification"
		label={m.justification()}
		cacheLock={cacheLocks['justification']}
		bind:cachedValue={formDataCache['justification']}
	/>
</div>
