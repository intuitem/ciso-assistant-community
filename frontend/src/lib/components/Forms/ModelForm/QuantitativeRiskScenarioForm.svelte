<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { run } from 'svelte/legacy';

	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	// Convert priority values from strings to integers for proper schema validation
	run(() => {
		if (model?.selectOptions?.priority) {
			model.selectOptions.priority.forEach((element) => {
				element.value = parseInt(element.value);
			});
		}
	});
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="quantitative-risk-studies"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="quantitative_risk_study"
	cacheLock={cacheLocks['quantitative_risk_study']}
	bind:cachedValue={formDataCache['quantitative_risk_study']}
	label="Quantitative Risk Study"
	hidden={initialData.quantitative_risk_study}
/>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<Checkbox {form} field="is_selected" label={m.isSelected()} helpText={m.isSelectedHelpText()} />
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
	optionsLabelField="auto"
	field="assets"
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
	label={m.assets()}
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="threats"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Select
		{form}
		options={model.selectOptions['priority']}
		field="priority"
		label={m.priority()}
		helpText={m.quantRiskPriorityHelpText()}
		cacheLock={cacheLocks['priority']}
		bind:cachedValue={formDataCache['priority']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="vulnerabilities"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="vulnerabilities"
		cacheLock={cacheLocks['vulnerabilities']}
		bind:cachedValue={formDataCache['vulnerabilities']}
		label={m.vulnerabilities()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="terminologies?field_path=qualifications&is_visible=true"
		optionsLabelField="translated_name"
		field="qualifications"
		cacheLock={cacheLocks['qualifications']}
		bind:cachedValue={formDataCache['qualifications']}
		label={m.qualifications()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="users?is_third_party=false"
		optionsLabelField="email"
		field="owner"
		cacheLock={cacheLocks['owner']}
		bind:cachedValue={formDataCache['owner']}
		label={m.owner()}
	/>
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
</Dropdown>
