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
		initialData.crq_studies ||
		initialData.ebios_studies ||
		initialData.entity_assessments ||
		initialData.findings_assessments;

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
	optionsEndpoint="users?is_approver=true&exclude_current=true"
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
		<label class="text-sm font-medium text-gray-700">{m.requestNotes()}</label>
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
	{#if object.expiration_date}
		<div class="space-y-2">
			<label class="text-sm font-medium text-gray-700">{m.expiryDate()}</label>
			<p class="p-3 bg-gray-50 rounded-lg text-sm">{object.expiration_date}</p>
		</div>
	{/if}
{:else}
	<TextField
		{form}
		type="date"
		field="expiration_date"
		label={m.expiryDate()}
		cacheLock={cacheLocks['expiration_date']}
		bind:cachedValue={formDataCache['expiration_date']}
		disabled={initialData.expiration_date}
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
			optionsEndpoint="quantitative-risk-studies"
			field="crq_studies"
			cacheLock={cacheLocks['crq_studies']}
			bind:cachedValue={formDataCache['crq_studies']}
			label={m.quantitativeRiskStudies()}
			multiple
			disabled={initialData.crq_studies}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="ebios-rm"
			field="ebios_studies"
			cacheLock={cacheLocks['ebios_studies']}
			bind:cachedValue={formDataCache['ebios_studies']}
			label={m.ebiosRMStudies()}
			multiple
			disabled={initialData.ebios_studies}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="entity-assessments"
			field="entity_assessments"
			cacheLock={cacheLocks['entity_assessments']}
			bind:cachedValue={formDataCache['entity_assessments']}
			label={m.entityAssessments()}
			multiple
			disabled={initialData.entity_assessments}
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
		<AutocompleteSelect
			{form}
			optionsEndpoint="evidences"
			field="evidences"
			cacheLock={cacheLocks['evidences']}
			bind:cachedValue={formDataCache['evidences']}
			label={m.evidences()}
			multiple
			disabled={initialData.evidences}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="security-exceptions"
			field="security_exceptions"
			cacheLock={cacheLocks['security_exceptions']}
			bind:cachedValue={formDataCache['security_exceptions']}
			label={m.securityExceptions()}
			multiple
			disabled={initialData.security_exceptions}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="policies"
			field="policies"
			cacheLock={cacheLocks['policies']}
			bind:cachedValue={formDataCache['policies']}
			label={m.policies()}
			multiple
			disabled={initialData.policies}
		/>
	</Dropdown>
{/if}
