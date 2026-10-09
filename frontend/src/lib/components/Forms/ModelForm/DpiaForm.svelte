<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context = 'default'
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	field="processing"
	optionsEndpoint="processings"
	optionsExtraFields={[['folder', 'str']]}
	cacheLock={cacheLocks['processing']}
	bind:cachedValue={formDataCache['processing']}
	label={m.processing()}
	hidden={initialData.processing}
/>
<AutocompleteSelect
	{form}
	multiple
	field="reasons"
	options={model.selectOptions['reasons']}
	cacheLock={cacheLocks['reasons']}
	bind:cachedValue={formDataCache['reasons']}
	label={m.reasons()}
	helpText={m.dpiaReasonsHelpText()}
/>
{#if context === 'create'}
	<AutocompleteSelect
		{form}
		field="risk_matrix"
		optionsEndpoint="risk-matrices"
		cacheLock={cacheLocks['risk_matrix']}
		bind:cachedValue={formDataCache['risk_matrix']}
		label={m.riskMatrix()}
		helpText={m.dpiaRiskMatrixHelpText()}
	/>
{/if}
<AutocompleteSelect
	{form}
	field="status"
	options={model.selectOptions['status']}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	label={m.status()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors?user__is_third_party=False"
	optionsLabelField="str"
	field="authors"
	cacheLock={cacheLocks['authors']}
	bind:cachedValue={formDataCache['authors']}
	label={m.authors()}
/>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-id-card"
	header={m.dpiaTechnicalSheet()}
>
	<TextField
		{form}
		field="ref_id"
		label={m.refId()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
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
		optionsEndpoint="actors?user__is_third_party=False"
		optionsLabelField="str"
		field="reviewers"
		cacheLock={cacheLocks['reviewers']}
		bind:cachedValue={formDataCache['reviewers']}
		label={m.reviewers()}
	/>
	<MarkdownField
		{form}
		field="scope_boundaries"
		label={m.scopeBoundaries()}
		cacheLock={cacheLocks['scope_boundaries']}
		bind:cachedValue={formDataCache['scope_boundaries']}
	/>
	<TextField
		type="date"
		{form}
		field="eta"
		label={m.eta()}
		cacheLock={cacheLocks['eta']}
		bind:cachedValue={formDataCache['eta']}
	/>
	<TextField
		type="date"
		{form}
		field="due_date"
		label={m.dueDate()}
		cacheLock={cacheLocks['due_date']}
		bind:cachedValue={formDataCache['due_date']}
	/>
</Dropdown>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-scale-balanced"
	header={m.dpiaNecessityProportionality()}
>
	<MarkdownField
		{form}
		field="necessity"
		label={m.necessity()}
		helpText={m.necessityHelpText()}
		cacheLock={cacheLocks['necessity']}
		bind:cachedValue={formDataCache['necessity']}
	/>
	<MarkdownField
		{form}
		field="proportionality"
		label={m.proportionality()}
		helpText={m.proportionalityHelpText()}
		cacheLock={cacheLocks['proportionality']}
		bind:cachedValue={formDataCache['proportionality']}
	/>
</Dropdown>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-shield-halved"
	header={m.dpiaRiskAssessment()}
>
	<MarkdownField
		{form}
		field="method_statement"
		label={m.methodStatement()}
		helpText={m.methodStatementHelpText()}
		cacheLock={cacheLocks['method_statement']}
		bind:cachedValue={formDataCache['method_statement']}
	/>
	{#if context !== 'create'}
		<AutocompleteSelect
			{form}
			field="design_risk_assessment"
			optionsEndpoint="risk-assessments"
			cacheLock={cacheLocks['design_risk_assessment']}
			bind:cachedValue={formDataCache['design_risk_assessment']}
			label={m.designRiskAssessment()}
		/>
		<AutocompleteSelect
			{form}
			field="incident_risk_assessment"
			optionsEndpoint="risk-assessments"
			cacheLock={cacheLocks['incident_risk_assessment']}
			bind:cachedValue={formDataCache['incident_risk_assessment']}
			label={m.incidentRiskAssessment()}
		/>
	{/if}
</Dropdown>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-comments"
	header={m.dpiaOpinions()}
>
	<MarkdownField
		{form}
		field="dpo_opinion"
		label={m.dpoOpinion()}
		cacheLock={cacheLocks['dpo_opinion']}
		bind:cachedValue={formDataCache['dpo_opinion']}
	/>
	<MarkdownField
		{form}
		field="dpo_advice_applied"
		label={m.dpoAdviceApplied()}
		cacheLock={cacheLocks['dpo_advice_applied']}
		bind:cachedValue={formDataCache['dpo_advice_applied']}
	/>
	<MarkdownField
		{form}
		field="data_subject_views"
		label={m.dataSubjectViews()}
		cacheLock={cacheLocks['data_subject_views']}
		bind:cachedValue={formDataCache['data_subject_views']}
	/>
	<MarkdownField
		{form}
		field="views_not_sought_reason"
		label={m.viewsNotSoughtReason()}
		cacheLock={cacheLocks['views_not_sought_reason']}
		bind:cachedValue={formDataCache['views_not_sought_reason']}
	/>
</Dropdown>

<Dropdown
	open={false}
	style="hover:text-primary-700"
	icon="fa-solid fa-gavel"
	header={m.decision()}
>
	<AutocompleteSelect
		{form}
		field="decision"
		options={model.selectOptions['decision']}
		cacheLock={cacheLocks['decision']}
		bind:cachedValue={formDataCache['decision']}
		label={m.decision()}
	/>
	<MarkdownField
		{form}
		field="conditions"
		label={m.conditions()}
		cacheLock={cacheLocks['conditions']}
		bind:cachedValue={formDataCache['conditions']}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="actors?user__is_third_party=False"
		optionsLabelField="str"
		field="validated_by"
		cacheLock={cacheLocks['validated_by']}
		bind:cachedValue={formDataCache['validated_by']}
		label={m.validatedBy()}
	/>
	<TextField
		type="date"
		{form}
		field="validated_at"
		label={m.validatedAt()}
		cacheLock={cacheLocks['validated_at']}
		bind:cachedValue={formDataCache['validated_at']}
	/>
	<TextField
		type="date"
		{form}
		field="review_due"
		label={m.reviewDue()}
		cacheLock={cacheLocks['review_due']}
		bind:cachedValue={formDataCache['review_due']}
	/>
</Dropdown>
