<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import * as m from '$paraglide/messages.js';
	import { getOptions } from '$lib/utils/crud';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';
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
	<TextArea
		{form}
		field="operating_modes_description"
		label={m.operatingModesDescription()}
		cacheLock={cacheLocks['operating_modes_description']}
		bind:cachedValue={formDataCache['operating_modes_description']}
		data-focusindex="1"
		helpText={m.operatingModesDescriptionHelpText()}
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
		helpText={m.operationalScenarioThreatsHelpText()}
	/>
	{#if context !== 'edit'}
		<AutocompleteSelect
			{form}
			options={getOptions({
				objects: model.foreignKeys['attack_path']
			})}
			field="attack_path"
			label={m.attackPath()}
		/>
	{/if}
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
		options={model.selectOptions['likelihood']}
		field="likelihood"
		label={m.likelihood()}
		cacheLock={cacheLocks['likelihood']}
		bind:cachedValue={formDataCache['likelihood']}
		helpText={m.likelihoodHelpText()}
	/>
	<TextArea
		{form}
		field="justification"
		label={m.justification()}
		cacheLock={cacheLocks['justification']}
		bind:cachedValue={formDataCache['justification']}
	/>
</div>
<Checkbox
	{form}
	field="is_selected"
	label={m.isSelected()}
	helpText={m.operationalScenarioIsSelectedHelpText()}
/>
