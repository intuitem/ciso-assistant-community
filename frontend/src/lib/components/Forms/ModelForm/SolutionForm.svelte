<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import Score from '../Score.svelte';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {}
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="entities"
	field="provider_entity"
	cacheLock={cacheLocks['provider_entity']}
	bind:cachedValue={formDataCache['provider_entity']}
	label={m.providerEntity()}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<Score
	{form}
	label={m.criticality()}
	field="criticality"
	inversedColors
	fullDonut
	min_score={1}
	max_score={4}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	label={m.owner()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
	field="assets"
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
	label={m.assets()}
/>
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	translateOptions={false}
	optionsLabelField="label"
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-clipboard-check"
	header={m.doraAssessment()}
>
	<AutocompleteSelect
		{form}
		field="dora_ict_service_type"
		options={model.selectOptions?.dora_ict_service_type}
		label={m.doraIctServiceType()}
		cacheLock={cacheLocks['dora_ict_service_type']}
		bind:cachedValue={formDataCache['dora_ict_service_type']}
		nullable
	/>
	<Checkbox
		{form}
		field="storage_of_data"
		label={m.storageOfData()}
		cacheLock={cacheLocks['storage_of_data']}
		bind:cachedValue={formDataCache['storage_of_data']}
		classesContainer="my-4"
	/>
	<AutocompleteSelect
		{form}
		field="data_location_storage"
		options={model.selectOptions?.data_location_storage}
		label={m.dataLocationStorage()}
		cacheLock={cacheLocks['data_location_storage']}
		bind:cachedValue={formDataCache['data_location_storage']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="data_location_processing"
		options={model.selectOptions?.data_location_processing}
		label={m.dataLocationProcessing()}
		cacheLock={cacheLocks['data_location_processing']}
		bind:cachedValue={formDataCache['data_location_processing']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_data_sensitiveness"
		options={model.selectOptions?.dora_data_sensitiveness}
		label={m.doraDataSensitiveness()}
		cacheLock={cacheLocks['dora_data_sensitiveness']}
		bind:cachedValue={formDataCache['dora_data_sensitiveness']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_reliance_level"
		options={model.selectOptions?.dora_reliance_level}
		label={m.doraRelianceLevel()}
		cacheLock={cacheLocks['dora_reliance_level']}
		bind:cachedValue={formDataCache['dora_reliance_level']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_substitutability"
		options={model.selectOptions?.dora_substitutability}
		label={m.doraSubstitutability()}
		cacheLock={cacheLocks['dora_substitutability']}
		bind:cachedValue={formDataCache['dora_substitutability']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_non_substitutability_reason"
		options={model.selectOptions?.dora_non_substitutability_reason}
		label={m.doraNonSubstitutabilityReason()}
		cacheLock={cacheLocks['dora_non_substitutability_reason']}
		bind:cachedValue={formDataCache['dora_non_substitutability_reason']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_has_exit_plan"
		options={model.selectOptions?.dora_has_exit_plan}
		label={m.doraHasExitPlan()}
		cacheLock={cacheLocks['dora_has_exit_plan']}
		bind:cachedValue={formDataCache['dora_has_exit_plan']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_reintegration_possibility"
		options={model.selectOptions?.dora_reintegration_possibility}
		label={m.doraReintegrationPossibility()}
		cacheLock={cacheLocks['dora_reintegration_possibility']}
		bind:cachedValue={formDataCache['dora_reintegration_possibility']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_discontinuing_impact"
		options={model.selectOptions?.dora_discontinuing_impact}
		label={m.doraDiscontinuingImpact()}
		cacheLock={cacheLocks['dora_discontinuing_impact']}
		bind:cachedValue={formDataCache['dora_discontinuing_impact']}
		nullable
	/>
	<AutocompleteSelect
		{form}
		field="dora_alternative_providers_identified"
		options={model.selectOptions?.dora_alternative_providers_identified}
		label={m.doraAlternativeProvidersIdentified()}
		cacheLock={cacheLocks['dora_alternative_providers_identified']}
		bind:cachedValue={formDataCache['dora_alternative_providers_identified']}
		nullable
	/>
	<TextField
		{form}
		field="dora_alternative_providers"
		label={m.doraAlternativeProviders()}
		cacheLock={cacheLocks['dora_alternative_providers']}
		bind:cachedValue={formDataCache['dora_alternative_providers']}
	/>
</Dropdown>
