<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { m } from '$paraglide/messages';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { getModalStore } from '$lib/components/Modals/stores';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context: string;
		object?: Record<string, any>;
		[key: string]: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context,
		object = {},
		...rest
	}: Props = $props();

	const modalStore = getModalStore();
	const formStore = (form as any).form;
	// Leaving the direct estimate replaces the likelihoods typed on operational scenarios
	const savedMethod = object?.quotation_method;
	let lastMethod = savedMethod;
	$effect(() => {
		const method = $formStore?.quotation_method;
		if (method === lastMethod) return;
		const leavingDirectEstimate = savedMethod === 'manual' && lastMethod === 'manual';
		lastMethod = method;
		if (!leavingDirectEstimate) return;
		modalStore.trigger({
			type: 'confirm',
			title: m.quotationMethodChangeTitle(),
			body: m.quotationMethodChangeBody(),
			response: (confirmed: boolean) => {
				if (confirmed) return;
				lastMethod = 'manual';
				formStore.update((data: Record<string, any>) => ({ ...data, quotation_method: 'manual' }));
			}
		});
	});

	let activeActivity: string | null = $state(null);
	const responsibilityMatricesEnabled = $derived(
		!!page.data?.featureflags?.responsibility_matrices
	);
	let hasEntities = $state(false);

	onMount(() => {
		fetch('/entities?limit=1')
			.then((r) => r.json())
			.then((data) => {
				hasEntities = (data.count ?? 0) > 0;
			})
			.catch(() => {});
	});

	page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		}
	});
</script>

{#if context !== 'ebiosRmStudy' && context !== 'selectAudit' && context !== 'selectAsset'}
	<TextField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
	<Select
		{form}
		options={model.selectOptions['quotation_method']}
		field="quotation_method"
		disableDoubleDash
		label={m.quotationMethod()}
		cacheLock={cacheLocks['quotation_method']}
		bind:cachedValue={formDataCache['quotation_method']}
	/>
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="classification-levels?is_visible=true&object_classification__is_visible=true"
		optionsLabelField="label"
		optionsExtraFields={[['object_classification', 'str']]}
		field="classification"
		label={m.classification()}
		helpText={m.ebiosRmStudyClassificationHelpText()}
		nullable
		cacheLock={cacheLocks['classification']}
		bind:cachedValue={formDataCache['classification']}
	/>
	{#if hasEntities}
		<AutocompleteSelect
			{form}
			optionsEndpoint="entities"
			optionsExtraFields={[['folder', 'str']]}
			field="reference_entity"
			cacheLock={cacheLocks['reference_entity']}
			bind:cachedValue={formDataCache['reference_entity']}
			label={m.referenceEntity()}
		/>
	{/if}
	<AutocompleteSelect
		{form}
		optionsEndpoint="risk-matrices?is_enabled=true"
		field="risk_matrix"
		cacheLock={cacheLocks['risk_matrix']}
		bind:cachedValue={formDataCache['risk_matrix']}
		label={m.riskMatrix()}
		helpText={m.ebiosRmMatrixHelpText()}
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
{:else if context === 'ebiosRmStudy'}
	<div
		class="relative p-2 space-y-2 rounded-md {activeActivity === 'one'
			? 'border-2 border-primary-500'
			: 'border-2 border-surface-300-700 border-dashed'}"
	>
		<p
			class="absolute -top-3 bg-surface-50-950 font-bold {activeActivity === 'one'
				? 'text-primary-500'
				: 'text-surface-600-400'}"
		>
			{m.activityOne()}
		</p>
		<FolderTreeSelect
			{form}
			field="folder"
			label={m.domain()}
			cacheLock={cacheLocks['folder']}
			bind:cachedValue={formDataCache['folder']}
			helpText={m.ebiosRmStudyDomainHelpText()}
		/>
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
			cacheLock={cacheLocks['status']}
			bind:cachedValue={formDataCache['status']}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="classification-levels?is_visible=true&object_classification__is_visible=true"
			optionsLabelField="label"
			optionsExtraFields={[['object_classification', 'str']]}
			field="classification"
			label={m.classification()}
			helpText={m.ebiosRmStudyClassificationHelpText()}
			nullable
			cacheLock={cacheLocks['classification']}
			bind:cachedValue={formDataCache['classification']}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="risk-matrices?is_enabled=true"
			field="risk_matrix"
			cacheLock={cacheLocks['risk_matrix']}
			bind:cachedValue={formDataCache['risk_matrix']}
			label={m.riskMatrix()}
			helpText={m.ebiosRmMatrixHelpText() + '\n' + m.riskAssessmentMatrixHelpText()}
		/>
		<TextField
			{form}
			field="version"
			label={m.version()}
			cacheLock={cacheLocks['version']}
			bind:cachedValue={formDataCache['version']}
		/>
		<Select
			{form}
			options={model.selectOptions['quotation_method']}
			field="quotation_method"
			disableDoubleDash
			label={m.quotationMethod()}
			cacheLock={cacheLocks['quotation_method']}
			bind:cachedValue={formDataCache['quotation_method']}
		/>
		{#if hasEntities}
			<AutocompleteSelect
				{form}
				optionsEndpoint="entities"
				optionsExtraFields={[['folder', 'str']]}
				field="reference_entity"
				cacheLock={cacheLocks['reference_entity']}
				bind:cachedValue={formDataCache['reference_entity']}
				label={m.referenceEntity()}
			/>
		{/if}
		<AutocompleteSelect
			multiple
			{form}
			optionsEndpoint="actors"
			optionsLabelField="str"
			optionsInfoFields={{
				fields: [{ field: 'type', translate: true }],
				position: 'prefix'
			}}
			field="authors"
			cacheLock={cacheLocks['authors']}
			bind:cachedValue={formDataCache['authors']}
			label={m.authors()}
		/>
		<AutocompleteSelect
			multiple
			{form}
			optionsEndpoint="actors"
			optionsLabelField="str"
			optionsInfoFields={{
				fields: [{ field: 'type', translate: true }],
				position: 'prefix'
			}}
			field="reviewers"
			cacheLock={cacheLocks['reviewers']}
			bind:cachedValue={formDataCache['reviewers']}
			label={m.reviewers()}
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
		<MarkdownField
			{form}
			field="objectives"
			label={m.objectives()}
			cacheLock={cacheLocks['objectives']}
			bind:cachedValue={formDataCache['objectives']}
		/>
		<MarkdownField
			{form}
			field="constraints_hypotheses"
			label={m.constraintsHypotheses()}
			cacheLock={cacheLocks['constraints_hypotheses']}
			bind:cachedValue={formDataCache['constraints_hypotheses']}
		/>
		{#if responsibilityMatricesEnabled}
			<AutocompleteSelect
				{form}
				optionsEndpoint="responsibility-matrices"
				optionsExtraFields={[['folder', 'str']]}
				field="responsibility_matrix"
				label={m.responsibilityMatrix()}
				helpText={m.ebiosRmStudyResponsibilityMatrixHelpText()}
				allowUserOptions
				nullable
				cacheLock={cacheLocks['responsibility_matrix']}
				bind:cachedValue={formDataCache['responsibility_matrix']}
			/>
		{/if}
	</div>
	<div
		class="relative p-2 space-y-2 rounded-md {activeActivity === 'two'
			? 'border-2 border-primary-500'
			: 'border-2 border-surface-300-700 border-dashed'}"
	>
		<p
			class="absolute -top-3 bg-surface-50-950 font-bold {activeActivity === 'two'
				? 'text-primary-500'
				: 'text-surface-600-400'}"
		>
			{m.activityTwo()}
		</p>
		<AutocompleteSelect
			multiple
			{form}
			optionsEndpoint="assets"
			optionsLabelField="auto"
			optionsExtraFields={[['folder', 'str']]}
			optionsDetailedUrlParameters={[
				rest?.scopeFolder?.id ? ['scope_folder_id', rest.scopeFolder.id] : ['', undefined]
			]}
			optionsInfoFields={{
				fields: [
					{
						field: 'type'
					}
				],
				classes: 'text-blue-500'
			}}
			field="assets"
			label={m.assets()}
			helpText={m.studyAssetHelpText()}
		/>
	</div>
	<MarkdownField
		{form}
		field="observation"
		label={m.executiveSummary()}
		helpText={m.ebiosRmExecutiveSummaryHelpText()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
{:else if context === 'selectAudit'}
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="compliance-assessments"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="compliance_assessments"
		cacheLock={cacheLocks['compliance_assessments']}
		bind:cachedValue={formDataCache['compliance_assessments']}
		label={m.complianceAssessment()}
	/>
{:else if context === 'selectAsset'}
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="assets"
		optionsExtraFields={[['folder', 'str']]}
		optionsDetailedUrlParameters={[
			rest?.scopeFolder?.id ? ['scope_folder_id', rest.scopeFolder.id] : ['', undefined]
		]}
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
{/if}
