<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Score from '../Score.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: Record<string, any>;
	}

	let {
		form,
		model = $bindable(),
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {}
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="perimeters"
	optionsExtraFields={[['folder', 'str']]}
	field="perimeter"
	cacheLock={cacheLocks['perimeter']}
	bind:cachedValue={formDataCache['perimeter']}
	label={m.perimeter()}
	hidden={initialData.perimeter}
/>
{#if !data.compliance_assessment}
	<Checkbox
		{form}
		field="create_audit"
		label={m.createAudit()}
		helpText={m.createAuditHelpText()}
	/>
	<AutocompleteSelect
		{form}
		disabled={!data.create_audit}
		mandatory
		hidden={!data.create_audit}
		optionsEndpoint="frameworks"
		field="framework"
		cacheLock={cacheLocks['framework']}
		bind:cachedValue={formDataCache['framework']}
		label={m.framework()}
		on:change={async (e) => {
			if (e.detail) {
				await fetch(`/frameworks/${e.detail}`)
					.then((r) => r.json())
					.then((r) => {
						const implementation_groups = r['implementation_groups_definition'] || [];
						model.selectOptions['selected_implementation_groups'] = implementation_groups.map(
							(group) => ({ label: group.name, value: group.ref_id })
						);
					});
			}
		}}
	/>
	{#if model.selectOptions['selected_implementation_groups'] && model.selectOptions['selected_implementation_groups'].length}
		<AutocompleteSelect
			multiple
			translateOptions={false}
			{form}
			options={model.selectOptions['selected_implementation_groups']}
			field="selected_implementation_groups"
			cacheLock={cacheLocks['selected_implementation_groups']}
			bind:cachedValue={formDataCache['selected_implementation_groups']}
			label={m.selectedImplementationGroups()}
		/>
	{/if}
{/if}
<AutocompleteSelect
	{form}
	optionsEndpoint="entities"
	field="entity"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
	hidden={initialData.entity}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="solutions"
	field="solutions"
	cacheLock={cacheLocks['solutions']}
	bind:cachedValue={formDataCache['solutions']}
	label={m.solutions()}
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
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	helpText={m.dueDateHelpText()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users?is_third_party=true"
	optionsLabelField="email"
	field="representatives"
	helpText={m.entityAssessmentRepresentativesHelpText()}
	cacheLock={cacheLocks['representatives']}
	bind:cachedValue={formDataCache['representatives']}
	label={m.representatives()}
/>
<Select
	{form}
	options={model.selectOptions['conclusion']}
	field="conclusion"
	label={m.conclusion()}
	cacheLock={cacheLocks['conclusion']}
	bind:cachedValue={formDataCache['conclusion']}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<TextField
		type="date"
		{form}
		field="eta"
		label={m.eta()}
		helpText={m.etaHelpText()}
		cacheLock={cacheLocks['eta']}
		bind:cachedValue={formDataCache['eta']}
	/>
	<TextField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="users?is_third_party=false"
		optionsLabelField="email"
		field="authors"
		cacheLock={cacheLocks['authors']}
		bind:cachedValue={formDataCache['authors']}
		label={m.authors()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="users?is_third_party=false"
		optionsLabelField="email"
		field="reviewers"
		cacheLock={cacheLocks['reviewers']}
		bind:cachedValue={formDataCache['reviewers']}
		label={m.reviewers()}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="compliance-assessments"
		optionsExtraFields={[['folder', 'str']]}
		field="compliance_assessment"
		cacheLock={cacheLocks['compliance_assessment']}
		bind:cachedValue={formDataCache['compliance_assessment']}
		label={m.complianceAssessment()}
		disabled={data.create_audit}
		hidden={data.create_audit}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="evidences"
		optionsExtraFields={[['folder', 'str']]}
		field="evidence"
		cacheLock={cacheLocks['evidence']}
		bind:cachedValue={formDataCache['evidence']}
		label={m.evidence()}
		helpText={m.entityAssessmentEvidenceHelpText()}
	/>
	<TextArea
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	<TextField
		{form}
		field="reference_link"
		label={m.referenceLink()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['reference_link']}
		bind:cachedValue={formDataCache['reference_link']}
	/>
</Dropdown>
