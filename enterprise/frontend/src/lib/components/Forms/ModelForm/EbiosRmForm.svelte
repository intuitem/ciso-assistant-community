<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { m } from '$paraglide/messages';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import { page } from '$app/state';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context
	}: Props = $props();

	let activeActivity: string | null = $state(null);

	page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		}
	});
</script>

{#if context !== 'selectAudit' && context !== 'selectAsset'}
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
		data-focusindex="0"
	/>
{/if}
{#if context !== 'ebiosRmStudy' && context !== 'selectAudit' && context !== 'selectAsset'}
	<TextField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
	<TextField
		{form}
		field="ref_id"
		label={m.refId()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="folders?content_type=DO"
		field="folder"
		pathField="path"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		hidden={initialData.folder}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="entities"
		field="reference_entity"
		cacheLock={cacheLocks['reference_entity']}
		bind:cachedValue={formDataCache['reference_entity']}
		label={m.referenceEntity()}
		hidden={initialData.reference_entity}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="risk-matrices"
		field="risk_matrix"
		cacheLock={cacheLocks['risk_matrix']}
		bind:cachedValue={formDataCache['risk_matrix']}
		label={m.riskMatrix()}
		placeholder={m.riskAssessmentMatrixHelpText()}
		helpText={m.ebiosRmMatrixHelpText()}
	/>
{:else if context === 'ebiosRmStudy'}
	<div
		class="relative p-2 space-y-2 rounded-md {activeActivity === 'one'
			? 'border-2 border-primary-500'
			: 'border-2 border-gray-300 border-dashed'}"
	>
		<p
			class="absolute -top-3 bg-white font-bold {activeActivity === 'one'
				? 'text-primary-500'
				: 'text-gray-500'}"
		>
			{m.activityOne()}
		</p>
		<TextArea
			{form}
			field="description"
			label={m.description()}
			cacheLock={cacheLocks['description']}
			bind:cachedValue={formDataCache['description']}
			data-focusindex="1"
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
		<TextField
			{form}
			field="ref_id"
			label={m.refId()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<AutocompleteSelect
			{form}
			optionsEndpoint="entities"
			field="reference_entity"
			cacheLock={cacheLocks['reference_entity']}
			bind:cachedValue={formDataCache['reference_entity']}
			label={m.referenceEntity()}
			hidden={initialData.reference_entity}
		/>
		<AutocompleteSelect
			multiple
			{form}
			optionsEndpoint="users?is_third_party=false"
			optionsLabelField="email"
			field="authors"
			cacheLock={cacheLocks['authors']}
			bind:cachedValue={formDataCache['authors']}
			label={m.authors()}
		/>
		<AutocompleteSelect
			multiple
			{form}
			optionsEndpoint="users?is_third_party=false"
			optionsLabelField="email"
			field="reviewers"
			cacheLock={cacheLocks['reviewers']}
			bind:cachedValue={formDataCache['reviewers']}
			label={m.reviewers()}
		/>
	</div>
	<div
		class="relative p-2 space-y-2 rounded-md {activeActivity === 'two'
			? 'border-2 border-primary-500'
			: 'border-2 border-gray-300 border-dashed'}"
	>
		<p
			class="absolute -top-3 bg-white font-bold {activeActivity === 'two'
				? 'text-primary-500'
				: 'text-gray-500'}"
		>
			{m.activityTwo()}
		</p>
		<AutocompleteSelect
			multiple
			{form}
			optionsEndpoint="assets"
			optionsExtraFields={[['folder', 'str']]}
			optionsInfoFields={{
				fields: [
					{
						field: 'type'
					}
				],
				color: 'blue'
			}}
			optionsLabelField="auto"
			field="assets"
			label={m.assets()}
		/>
	</div>
	<TextArea
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
{:else if context === 'selectAudit'}
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="compliance-assessments"
		optionsExtraFields={[['perimeter', 'str']]}
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
		optionsInfoFields={{
			fields: [
				{
					field: 'type'
				}
			],
			color: 'blue'
		}}
		optionsLabelField="auto"
		field="assets"
		cacheLock={cacheLocks['assets']}
		bind:cachedValue={formDataCache['assets']}
		label={m.assets()}
	/>
{/if}
