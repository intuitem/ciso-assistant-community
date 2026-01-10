<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		object?: Record<string, any>;
		initialData?: Record<string, any>;
		updated_fields?: Set<string>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		object = {},
		initialData = {},
		updated_fields = new Set()
	}: Props = $props();

	// Check if we're coming from a specific assessment context
	const hasPresetAssessments =
		initialData.risk_assessments ||
		initialData.compliance_assessments ||
		initialData.business_impact_analysis ||
		initialData.crq_studies ||
		initialData.ebios_studies ||
		initialData.entity_assessments ||
		initialData.findings_assessments;

	// Determine the approver endpoint based on allow_self_validation setting
	const allowSelfValidation = $derived(page.data?.settings?.allow_self_validation ?? false);
	const approverEndpoint = $derived(
		allowSelfValidation ? 'users?is_approver=true' : 'users?is_approver=true&exclude_current=true'
	);

	async function fetchDefaultRefId() {
		try {
			const response = await fetch(`/validation-flows/default-ref-id/`);
			const result = await response.json();
			if (response.ok && result.results) {
				form.form.update((currentData) => {
					updated_fields.add('ref_id');
					return { ...currentData, ref_id: result.results };
				});
			} else {
				console.error(result.error || 'Failed to fetch default ref_id');
			}
		} catch (error) {
			console.error('Error fetching default ref_id:', error);
		}
	}
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint={approverEndpoint}
	optionsLabelField="email"
	field="approver"
	cacheLock={cacheLocks['approver']}
	bind:cachedValue={formDataCache['approver']}
	label={m.approver()}
	helpText={m.validationApproverHelpText()}
	disabled={initialData.approver}
/>
{#if object?.id}
	<div class="space-y-2">
		<span class="text-sm font-medium text-gray-700">{m.requestNotes()}</span>
		<MarkdownRenderer content={object.request_notes} class="p-3 bg-gray-50 rounded-lg" />
	</div>
{:else}
	<TextArea
		{form}
		field="request_notes"
		label={m.requestNotes()}
		cacheLock={cacheLocks['request_notes']}
		bind:cachedValue={formDataCache['request_notes']}
	/>
{/if}
{#if !object?.id}
	<AutocompleteSelect
		{form}
		optionsEndpoint="filtering-labels"
		field="filtering_labels"
		optionsLabelField="label"
		cacheLock={cacheLocks['filtering_labels']}
		bind:cachedValue={formDataCache['filtering_labels']}
		label={m.labels()}
		multiple
	/>
{/if}
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
	onChange={async (e) => {
		if (e && !object?.id) {
			await fetchDefaultRefId();
		}
	}}
/>
{#if object?.id}
	<Select
		{form}
		field="status"
		options={model.selectOptions['status']}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
		label={m.status()}
		disableDoubleDash={true}
	/>
{/if}
{#if object?.id}
	{#if object.validation_deadline}
		<div class="space-y-2">
			<span class="text-sm font-medium text-gray-700">{m.validationDeadline()}</span>
			<p class="p-3 bg-gray-50 rounded-lg text-sm">{object.validation_deadline}</p>
		</div>
	{/if}
{:else}
	<TextField
		{form}
		type="date"
		field="validation_deadline"
		label={m.validationDeadline()}
		cacheLock={cacheLocks['validation_deadline']}
		bind:cachedValue={formDataCache['validation_deadline']}
		disabled={initialData.validation_deadline}
	/>
{/if}
{#if !hasPresetAssessments}
	<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
		<TextField
			{form}
			field="ref_id"
			label={m.refId()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
			disabled={initialData.ref_id}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="compliance-assessments"
			field="compliance_assessments"
			cacheLock={cacheLocks['compliance_assessments']}
			bind:cachedValue={formDataCache['compliance_assessments']}
			label={m.complianceAssessments()}
			multiple
			disabled={initialData.compliance_assessments}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="risk-assessments"
			field="risk_assessments"
			cacheLock={cacheLocks['risk_assessments']}
			bind:cachedValue={formDataCache['risk_assessments']}
			label={m.riskAssessments()}
			multiple
			disabled={initialData.risk_assessments}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="business-impact-analysis"
			field="business_impact_analysis"
			cacheLock={cacheLocks['business_impact_analysis']}
			bind:cachedValue={formDataCache['business_impact_analysis']}
			label={m.businessImpactAnalysis()}
			multiple
			disabled={initialData.business_impact_analysis}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="findings-assessments"
			field="findings_assessments"
			cacheLock={cacheLocks['findings_assessments']}
			bind:cachedValue={formDataCache['findings_assessments']}
			label={m.findingsAssessments()}
			multiple
			disabled={initialData.findings_assessments}
		/>
	</Dropdown>
{/if}
