<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { m } from '$paraglide/messages';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';
	import { page } from '$app/state';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context: string;
		object?: any; // Optional object for additional data
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context,
		object = null // Optional object for additional data
	}: Props = $props();

	const activityBackground = context === 'edit' ? 'bg-white' : 'bg-surface-100-900';

	let activeActivity: string | null = $state(null);
	page.url.searchParams.forEach((value, key) => {
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
	field="ebios_rm_study"
	cacheLock={cacheLocks['ebios_rm_study']}
	bind:cachedValue={formDataCache['ebios_rm_study']}
	label={m.ebiosRmStudy()}
	hidden={initialData.ebios_rm_study}
/>
<AutocompleteSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.folder()}
	hidden
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
	{#if context !== 'edit'}
		<AutocompleteSelect
			{form}
			optionsEndpoint="attack-paths?is_selected=true&used=false"
			optionsDetailedUrlParameters={[['ebios_rm_study', initialData.ebios_rm_study]]}
			field="attack_path"
			label={m.attackPath() + ` (${m.strategicScenario()})`}
		/>
	{/if}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="threats"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="threats"
		cacheLock={cacheLocks['threats']}
		bind:cachedValue={formDataCache['threats']}
		label={m.elementaryActionsTechniques()}
		helpText={m.operationalScenarioThreatsHelpText()}
	/>
	<TextArea
		{form}
		field="operating_modes_description"
		label={m.operatingModesDescription()}
		cacheLock={cacheLocks['operating_modes_description']}
		bind:cachedValue={formDataCache['operating_modes_description']}
		data-focusindex="1"
		helpText={m.operatingModesDescriptionHelpText()}
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
	{#if object.quotation_method === 'manual'}
		<Select
			{form}
			options={model.selectOptions['likelihood']}
			field="likelihood"
			label={m.likelihood()}
			cacheLock={cacheLocks['likelihood']}
			bind:cachedValue={formDataCache['likelihood']}
			helpText={m.likelihoodHelpText()}
		/>
	{/if}
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
