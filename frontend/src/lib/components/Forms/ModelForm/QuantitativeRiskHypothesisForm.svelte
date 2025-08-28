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
	label={m.quantitativeRiskScenario()}
	hidden={initialData.quantitative_risk_scenario}
/>

<Select
	{form}
	options={model.selectOptions['risk_stage']}
	translateOptions={true}
	disableDoubleDash
	field="risk_stage"
	label={m.hypothesisStage()}
	cacheLock={cacheLocks['risk_stage']}
	bind:cachedValue={formDataCache['risk_stage']}
/>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-shield-halved"
	header={m.treatment()}
>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="applied-controls"
		optionsExtraFields={[['folder', 'str']]}
		field="existing_applied_controls"
		cacheLock={cacheLocks['existing_applied_controls']}
		bind:cachedValue={formDataCache['existing_applied_controls']}
		label={m.existingControls()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="applied-controls"
		optionsExtraFields={[['folder', 'str']]}
		field="added_applied_controls"
		cacheLock={cacheLocks['added_applied_controls']}
		bind:cachedValue={formDataCache['added_applied_controls']}
		label={m.addedControls()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="applied-controls"
		optionsExtraFields={[['folder', 'str']]}
		field="removed_applied_controls"
		cacheLock={cacheLocks['removed_applied_controls']}
		bind:cachedValue={formDataCache['removed_applied_controls']}
		label={m.removedControls()}
	/>
</Dropdown>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-calculator"
	header={m.simulationParameters()}
>
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
		helpText={m.probabilityHelpText()}
	/>
	<TextField
		{form}
		field="impact.lb"
		label={m.expectedLossLowerBound()}
		type="number"
		step="10"
		min="10"
		cacheLock={cacheLocks['impact.lb']}
		bind:cachedValue={formDataCache['impact.lb']}
		helpText={m.lowerBoundHelpText()}
	/>
	<TextField
		{form}
		field="impact.ub"
		label={m.expectedLossUpperBound()}
		type="number"
		step="10"
		min="20"
		cacheLock={cacheLocks['impact.ub']}
		bind:cachedValue={formDataCache['impact.ub']}
		helpText={m.upperBoundHelpText()}
	/>
</Dropdown>

<MarkdownField
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>

<Checkbox {form} field="is_selected" label={m.isSelected()} />
