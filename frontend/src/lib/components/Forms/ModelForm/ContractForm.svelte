<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

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
	field="folder"
	optionsEndpoint="folders"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<AutocompleteSelect
	{form}
	field="status"
	options={model.selectOptions?.status}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	label={m.status()}
/>
<AutocompleteSelect
	{form}
	field="dora_contractual_arrangement"
	options={model.selectOptions?.dora_contractual_arrangement}
	label={m.doraContractualArrangement()}
	nullable={false}
	cacheLock={cacheLocks['dora_contractual_arrangement']}
	bind:cachedValue={formDataCache['dora_contractual_arrangement']}
/>
<TextField
	type="date"
	{form}
	field="start_date"
	label={m.startDate()}
	cacheLock={cacheLocks['start_date']}
	bind:cachedValue={formDataCache['start_date']}
/>
<TextField
	type="date"
	{form}
	field="end_date"
	label={m.endDate()}
	cacheLock={cacheLocks['end_date']}
	bind:cachedValue={formDataCache['end_date']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="entities"
	field="entities"
	cacheLock={cacheLocks['entities']}
	bind:cachedValue={formDataCache['entities']}
	label={m.entities()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="solutions"
	optionsExtraFields={[['provider_entity', 'str']]}
	field="solutions"
	cacheLock={cacheLocks['solutions']}
	bind:cachedValue={formDataCache['solutions']}
	label={m.solutions()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="evidences"
	optionsExtraFields={[['folder', 'str']]}
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.documents()}
/>
<AutocompleteSelect
	{form}
	multiple
	field="filtering_labels"
	optionsEndpoint="filtering-labels"
	cacheLock={cacheLocks['filtering_labels']}
	bind:cachedValue={formDataCache['filtering_labels']}
	label={m.filteringLabels()}
/>

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-ellipsis" header={m.more()}>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="users"
		optionsLabelField="email"
		field="owner"
		cacheLock={cacheLocks['owner']}
		bind:cachedValue={formDataCache['owner']}
		label={m.owner()}
	/>
	<AutocompleteSelect
		{form}
		field="overarching_contract"
		optionsEndpoint="contracts?dora_contractual_arrangement=eba_CO:x2"
		optionsExtraFields={[['folder', 'str']]}
		label={m.overarchingContract()}
		helpText={m.overarchingContractHelpText()}
		cacheLock={cacheLocks['overarching_contract']}
		bind:cachedValue={formDataCache['overarching_contract']}
	/>
	<AutocompleteSelect
		{form}
		field="currency"
		options={model.selectOptions?.currency}
		label={m.currency()}
		cacheLock={cacheLocks['currency']}
		bind:cachedValue={formDataCache['currency']}
	/>
	<NumberField
		{form}
		field="annual_expense"
		label={m.annualExpense()}
		cacheLock={cacheLocks['annual_expense']}
		bind:cachedValue={formDataCache['annual_expense']}
	/>
	<AutocompleteSelect
		{form}
		field="termination_reason"
		options={model.selectOptions?.termination_reason}
		label={m.terminationReason()}
		cacheLock={cacheLocks['termination_reason']}
		bind:cachedValue={formDataCache['termination_reason']}
	/>
	<AutocompleteSelect
		{form}
		field="governing_law_country"
		options={model.selectOptions?.governing_law_country}
		label={m.governingLawCountry()}
		cacheLock={cacheLocks['governing_law_country']}
		bind:cachedValue={formDataCache['governing_law_country']}
	/>
	<NumberField
		{form}
		field="notice_period_entity"
		label={m.noticePeriodEntity()}
		cacheLock={cacheLocks['notice_period_entity']}
		bind:cachedValue={formDataCache['notice_period_entity']}
	/>
	<NumberField
		{form}
		field="notice_period_provider"
		label={m.noticePeriodProvider()}
		cacheLock={cacheLocks['notice_period_provider']}
		bind:cachedValue={formDataCache['notice_period_provider']}
	/>
	<Checkbox
		{form}
		field="is_intragroup"
		label={m.isIntragroup()}
		cacheLock={cacheLocks['is_intragroup']}
		bind:cachedValue={formDataCache['is_intragroup']}
	/>
</Dropdown>
