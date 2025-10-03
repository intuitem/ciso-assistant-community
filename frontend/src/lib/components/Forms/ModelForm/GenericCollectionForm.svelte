<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '../TextField.svelte';
	import MarkdownField from '../MarkdownField.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = ''
	}: Props = $props();
</script>

{#if context === 'selectComplianceAssessments'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="compliance-assessments"
		optionsExtraFields={[['perimeter', 'str']]}
		optionsLabelField="auto"
		field="compliance_assessments"
		cacheLock={cacheLocks['compliance_assessments']}
		bind:cachedValue={formDataCache['compliance_assessments']}
		label={m.complianceAssessments()}
	/>
{:else if context === 'selectRiskAssessments'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="risk-assessments"
		optionsExtraFields={[['perimeter', 'str']]}
		optionsLabelField="auto"
		field="risk_assessments"
		cacheLock={cacheLocks['risk_assessments']}
		bind:cachedValue={formDataCache['risk_assessments']}
		label={m.riskAssessments()}
	/>
{:else if context === 'selectCrqStudies'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="quantitative-risk-studies"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="crq_studies"
		cacheLock={cacheLocks['crq_studies']}
		bind:cachedValue={formDataCache['crq_studies']}
		label={m.quantitativeRiskStudies()}
	/>
{:else if context === 'selectEbiosStudies'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="ebios-rm"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="ebios_studies"
		cacheLock={cacheLocks['ebios_studies']}
		bind:cachedValue={formDataCache['ebios_studies']}
		label={m.ebiosRmStudies()}
	/>
{:else if context === 'selectEntityAssessments'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="entity-assessments"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="entity_assessments"
		cacheLock={cacheLocks['entity_assessments']}
		bind:cachedValue={formDataCache['entity_assessments']}
		label={m.entityAssessments()}
	/>
{:else if context === 'selectFindingsAssessments'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="findings-assessments"
		optionsExtraFields={[['perimeter', 'str']]}
		optionsLabelField="auto"
		field="findings_assessments"
		cacheLock={cacheLocks['findings_assessments']}
		bind:cachedValue={formDataCache['findings_assessments']}
		label={m.findingsAssessments()}
	/>
{:else if context === 'selectDocuments'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="evidences"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="documents"
		cacheLock={cacheLocks['documents']}
		bind:cachedValue={formDataCache['documents']}
		label={m.documents()}
	/>
{:else if context === 'selectSecurityExceptions'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="security-exceptions"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="security_exceptions"
		cacheLock={cacheLocks['security_exceptions']}
		bind:cachedValue={formDataCache['security_exceptions']}
		label={m.securityExceptions()}
	/>
{:else if context === 'selectPolicies'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="policies"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="policies"
		cacheLock={cacheLocks['policies']}
		bind:cachedValue={formDataCache['policies']}
		label={m.policies()}
	/>
	<!-- {:else if context === 'selectDependencies'} -->
	<!-- 	<AutocompleteSelect -->
	<!-- 		{form} -->
	<!-- 		multiple -->
	<!-- 		optionsEndpoint="generic-collections" -->
	<!-- 		optionsLabelField="auto" -->
	<!-- 		optionsSelf={object} -->
	<!-- 		field="dependencies" -->
	<!-- 		cacheLock={cacheLocks['dependencies']} -->
	<!-- 		bind:cachedValue={formDataCache['dependencies']} -->
	<!-- 		label={m.dependencies()} -->
	<!-- 	/> -->
{:else}
	<TextField
		{form}
		field="ref_id"
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
		label={m.refId()}
	/>

	<AutocompleteSelect
		{form}
		optionsEndpoint="folders?content_type=DO&content_type=GL"
		pathField="path"
		field="folder"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		hidden={initialData.folder}
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
	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-link"
		header={m.relationships()}
	>
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="compliance-assessments"
			optionsExtraFields={[['perimeter', 'str']]}
			optionsLabelField="auto"
			field="compliance_assessments"
			cacheLock={cacheLocks['compliance_assessments']}
			bind:cachedValue={formDataCache['compliance_assessments']}
			label={m.complianceAssessments()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="risk-assessments"
			optionsExtraFields={[['perimeter', 'str']]}
			optionsLabelField="auto"
			field="risk_assessments"
			cacheLock={cacheLocks['risk_assessments']}
			bind:cachedValue={formDataCache['risk_assessments']}
			label={m.riskAssessments()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="quantitative-risk-studies"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="crq_studies"
			cacheLock={cacheLocks['crq_studies']}
			bind:cachedValue={formDataCache['crq_studies']}
			label={m.quantitativeRiskStudies()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="ebios-rm"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="ebios_studies"
			cacheLock={cacheLocks['ebios_studies']}
			bind:cachedValue={formDataCache['ebios_studies']}
			label={m.ebiosRmStudies()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="entity-assessments"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="entity_assessments"
			cacheLock={cacheLocks['entity_assessments']}
			bind:cachedValue={formDataCache['entity_assessments']}
			label={m.entityAssessments()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="findings-assessments"
			optionsExtraFields={[['perimeter', 'str']]}
			optionsLabelField="auto"
			field="findings_assessments"
			cacheLock={cacheLocks['findings_assessments']}
			bind:cachedValue={formDataCache['findings_assessments']}
			label={m.findingsAssessments()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="evidences"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="documents"
			cacheLock={cacheLocks['documents']}
			bind:cachedValue={formDataCache['documents']}
			label={m.evidences()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="security-exceptions"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="security_exceptions"
			cacheLock={cacheLocks['security_exceptions']}
			bind:cachedValue={formDataCache['security_exceptions']}
			label={m.securityExceptions()}
		/>

		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="policies"
			optionsExtraFields={[['folder', 'str']]}
			optionsLabelField="auto"
			field="policies"
			cacheLock={cacheLocks['policies']}
			bind:cachedValue={formDataCache['policies']}
			label={m.policies()}
		/>

		<!-- <AutocompleteSelect -->
		<!-- 	{form} -->
		<!-- 	multiple -->
		<!-- 	optionsEndpoint="generic-collections" -->
		<!-- 	optionsLabelField="auto" -->
		<!-- 	optionsSelf={object} -->
		<!-- 	field="dependencies" -->
		<!-- 	cacheLock={cacheLocks['dependencies']} -->
		<!-- 	bind:cachedValue={formDataCache['dependencies']} -->
		<!-- 	label={m.dependencies()} -->
		<!-- /> -->
	</Dropdown>
{/if}
