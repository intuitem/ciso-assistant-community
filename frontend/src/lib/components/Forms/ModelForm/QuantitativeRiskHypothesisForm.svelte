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

<Select
	{form}
	options={model.selectOptions['risk_stage']}
	translateOptions={true}
  disableDoubleDash
	field="risk_stage"
	label="Hypothesis stage"
	cacheLock={cacheLocks['risk_stage']}
	bind:cachedValue={formDataCache['risk_stage']}
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="existing_applied_controls"
	cacheLock={cacheLocks['existing_applied_controls']}
	bind:cachedValue={formDataCache['existing_applied_controls']}
	label="Existing Controls"
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="added_applied_controls"
	cacheLock={cacheLocks['added_applied_controls']}
	bind:cachedValue={formDataCache['added_applied_controls']}
	label="Added Controls"
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="removed_applied_controls"
	cacheLock={cacheLocks['removed_applied_controls']}
	bind:cachedValue={formDataCache['removed_applied_controls']}
	label="Removed Controls"
/>
<input type="hidden" name="impact.distribution" value="LOGNORMAL-CI90" />
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
	helpText="Estimated probability value between 0 and 1, based on the knowledge you have"
/>

<TextField
	{form}
	field="impact.lb"
	label="Expected Loss Lower Bound (LB)"
	type="number"
	step="10"
	min="10"
	cacheLock={cacheLocks['impact.lb']}
	bind:cachedValue={formDataCache['impact.lb']}
	helpText="Remember that, given the current distribution, 5% of the time it will be LOWER than this."
/>

<TextField
	{form}
	field="impact.ub"
	label="Expected Loss Upper Bound (UB)"
	type="number"
	step="10"
	min="20"
	cacheLock={cacheLocks['impact.ub']}
	bind:cachedValue={formDataCache['impact.ub']}
	helpText="Remember that, given the current distribution, 5% of the time it will be HIGHER than this."
/>


<MarkdownField
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>

	<Checkbox
		{form}
		field="is_selected"
		label={m.isSelected()}
		helpText={m.roToIsSelectedHelpText()}
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
