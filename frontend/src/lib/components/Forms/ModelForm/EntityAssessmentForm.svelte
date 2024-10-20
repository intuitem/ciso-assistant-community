<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Score from '../Score.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let data: Record<string, any> = {};
</script>

<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['project'] })}
	field="project"
	cacheLock={cacheLocks['project']}
	bind:cachedValue={formDataCache['project']}
	label={m.project()}
	hidden={initialData.project}
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
		options={getOptions({ objects: model.foreignKeys['framework'] })}
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
	options={getOptions({ objects: model.foreignKeys['entity'] })}
	field="entity"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
	hidden={initialData.entity}
/>
<AutocompleteSelect
	{form}
	multiple
	options={getOptions({ objects: model.foreignKeys['solutions'] })}
	field="solutions"
	cacheLock={cacheLocks['solutions']}
	bind:cachedValue={formDataCache['solutions']}
	label={m.solutions()}
/>
<Score
	{form}
	label={m.criticality()}
	field="criticality"
	always_enabled={true}
	inversedColors
	fullDonut
	min_score={1}
	max_score={4}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<TextField
	{form}
	field="version"
	label={m.version()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
<TextField
	{form}
	field="reference_link"
	label={m.referenceLink()}
	helpText={m.linkHelpText()}
	cacheLock={cacheLocks['reference_link']}
	bind:cachedValue={formDataCache['reference_link']}
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
	options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
	field="authors"
	cacheLock={cacheLocks['authors']}
	bind:cachedValue={formDataCache['authors']}
	label={m.authors()}
/>
<AutocompleteSelect
	{form}
	multiple
	options={getOptions({ objects: model.foreignKeys['representatives'], label: 'email' })}
	field="representatives"
	helpText={m.entityAssessmentRepresentativesHelpText()}
	cacheLock={cacheLocks['representatives']}
	bind:cachedValue={formDataCache['representatives']}
	label={m.representatives()}
/>
<AutocompleteSelect
	{form}
	multiple
	options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
	field="reviewers"
	cacheLock={cacheLocks['reviewers']}
	bind:cachedValue={formDataCache['reviewers']}
	label={m.reviewers()}
/>
<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['compliance_assessment'] })}
	field="compliance_assessment"
	cacheLock={cacheLocks['compliance_assessment']}
	bind:cachedValue={formDataCache['compliance_assessment']}
	label={m.complianceAssessment()}
	disabled={data.create_audit}
	hidden={data.create_audit}
/>
<AutocompleteSelect
	{form}
	options={getOptions({
		objects: model.foreignKeys['evidence'],
		extra_fields: [['folder', 'str']]
	})}
	field="evidence"
	cacheLock={cacheLocks['evidence']}
	bind:cachedValue={formDataCache['evidence']}
	label={m.evidence()}
	helpText={m.entityAssessmentEvidenceHelpText()}
/>
<Select
	{form}
	options={model.selectOptions['conclusion']}
	field="conclusion"
	label={m.conclusion()}
	cacheLock={cacheLocks['conclusion']}
	bind:cachedValue={formDataCache['conclusion']}
/>
<TextArea
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
<!-- <Score {form} label={m.penetration()} field="penetration" always_enabled={true} inversedColors fullDonut max_score={5} />
<Score {form} label={m.dependency()} field="dependency" always_enabled={true} inversedColors fullDonut max_score={5} />
<Score {form} label={m.maturity()} field="maturity" always_enabled={true} inversedColors fullDonut max_score={5} />
<Score {form} label={m.trust()} field="trust" always_enabled={true} inversedColors fullDonut max_score={5} /> -->
