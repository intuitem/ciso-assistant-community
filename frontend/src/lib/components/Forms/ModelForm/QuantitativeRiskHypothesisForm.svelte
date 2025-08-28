<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';

	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
		context?: string;
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = 'default'
	}: Props = $props();
</script>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="quantitative-risk-scenarios"
	field="quantitative_risk_scenario"
	cacheLock={cacheLocks['quantitative_risk_scenario']}
	bind:cachedValue={formDataCache['quantitative_risk_scenario']}
	label="Quantitative Risk Scenario"
	hidden={initialData.quantitative_risk_scenario}
/>

	<Checkbox
		{form}
		field="is_selected"
		label={m.isSelected()}
		helpText={m.roToIsSelectedHelpText()}
	/>
<Select
	{form}
	options={model.selectOptions['risk_stage']}
	translateOptions={false}
	field="risk_stage"
	label="Risk Stage"
	cacheLock={cacheLocks['risk_stage']}
	bind:cachedValue={formDataCache['risk_stage']}
/>

<TextField
	{form}
	field="probability"
	label="Probability (P)"
	type="number"
	step="0.01"
	min="0"
	max="1"
	cacheLock={cacheLocks['probability']}
	bind:cachedValue={formDataCache['probability']}
	helpText="Probability value between 0 and 1"
/>

<input type="hidden" name="impact.distribution" value="LOGNORMAL" />

<TextField
	{form}
	field="impact.lb"
	label="Impact Lower Bound (LB)"
	type="number"
	step="0.01"
	min="0"
	cacheLock={cacheLocks['impact.lb']}
	bind:cachedValue={formDataCache['impact.lb']}
	helpText="Lower bound for impact distribution"
/>

<TextField
	{form}
	field="impact.ub"
	label="Impact Upper Bound (UB)"
	type="number"
	step="0.01"
	min="0"
	cacheLock={cacheLocks['impact.ub']}
	bind:cachedValue={formDataCache['impact.ub']}
	helpText="Upper bound for impact distribution"
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="existing_applied_controls"
	cacheLock={cacheLocks['existing_applied_controls']}
	bind:cachedValue={formDataCache['existing_applied_controls']}
	label="Existing Applied Controls"
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="added_applied_controls"
	cacheLock={cacheLocks['added_applied_controls']}
	bind:cachedValue={formDataCache['added_applied_controls']}
	label="Added Applied Controls"
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="removed_applied_controls"
	cacheLock={cacheLocks['removed_applied_controls']}
	bind:cachedValue={formDataCache['removed_applied_controls']}
	label="Removed Applied Controls"
/>

<MarkdownField
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>

<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	translateOptions={false}
	allowUserOptions="append"
/>
