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
	hidden={initialData.provider_entity}
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

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-scale-balanced"
	header={m.doraSpecific()}
>
	<AutocompleteSelect
		{form}
		field="dora_ict_service_type"
		options={model.selectOptions?.dora_ict_service_type}
		label={m.doraIctServiceType()}
		cacheLock={cacheLocks['dora_ict_service_type']}
		bind:cachedValue={formDataCache['dora_ict_service_type']}
	/>
	<Checkbox
		{form}
		field="storage_of_data"
		label={m.storageOfData()}
		cacheLock={cacheLocks['storage_of_data']}
		bind:cachedValue={formDataCache['storage_of_data']}
	/>
	<AutocompleteSelect
		{form}
		field="data_location_storage"
		options={model.selectOptions?.data_location_storage}
		label={m.dataLocationStorage()}
		cacheLock={cacheLocks['data_location_storage']}
		bind:cachedValue={formDataCache['data_location_storage']}
	/>
	<AutocompleteSelect
		{form}
		field="data_location_processing"
		options={model.selectOptions?.data_location_processing}
		label={m.dataLocationProcessing()}
		cacheLock={cacheLocks['data_location_processing']}
		bind:cachedValue={formDataCache['data_location_processing']}
	/>
	<AutocompleteSelect
		{form}
		field="dora_data_sensitiveness"
		options={model.selectOptions?.dora_data_sensitiveness}
		label={m.doraDataSensitiveness()}
		cacheLock={cacheLocks['dora_data_sensitiveness']}
		bind:cachedValue={formDataCache['dora_data_sensitiveness']}
	/>
	<AutocompleteSelect
		{form}
		field="dora_reliance_level"
		options={model.selectOptions?.dora_reliance_level}
		label={m.doraRelianceLevel()}
		cacheLock={cacheLocks['dora_reliance_level']}
		bind:cachedValue={formDataCache['dora_reliance_level']}
	/>
</Dropdown>
