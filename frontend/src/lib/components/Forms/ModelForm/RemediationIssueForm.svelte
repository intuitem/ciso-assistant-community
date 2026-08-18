<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

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

<div class="rounded-sm border border-primary-300 bg-primary-50 p-2 text-sm text-primary-800">
	{m.remediationIssueNotice()}
</div>

<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<Select
	{form}
	options={model.selectOptions['priority']}
	field="priority"
	label={m.priority()}
	cacheLock={cacheLocks['priority']}
	bind:cachedValue={formDataCache['priority']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="lead_representatives"
	cacheLock={cacheLocks['lead_representatives']}
	bind:cachedValue={formDataCache['lead_representatives']}
	label={m.leadRepresentatives()}
	helpText={m.representativesHelpText()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="respondent_representatives"
	cacheLock={cacheLocks['respondent_representatives']}
	bind:cachedValue={formDataCache['respondent_representatives']}
	label={m.respondentRepresentatives()}
	helpText={m.representativesHelpText()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="lead_contributors"
	cacheLock={cacheLocks['lead_contributors']}
	bind:cachedValue={formDataCache['lead_contributors']}
	label={m.leadContributors()}
	helpText={m.contributorsHelpText()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="respondent_contributors"
	cacheLock={cacheLocks['respondent_contributors']}
	bind:cachedValue={formDataCache['respondent_contributors']}
	label={m.respondentContributors()}
	helpText={m.contributorsHelpText()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="requirement-assessments"
	optionsLabelField="str"
	field="requirement_assessments"
	cacheLock={cacheLocks['requirement_assessments']}
	bind:cachedValue={formDataCache['requirement_assessments']}
	label={m.requirementAssessments()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="findings"
	field="findings"
	cacheLock={cacheLocks['findings']}
	bind:cachedValue={formDataCache['findings']}
	label={m.findings()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	field="applied_controls"
	cacheLock={cacheLocks['applied_controls']}
	bind:cachedValue={formDataCache['applied_controls']}
	label={m.appliedControls()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="evidences"
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.evidences()}
/>
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	translateOptions={false}
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>
