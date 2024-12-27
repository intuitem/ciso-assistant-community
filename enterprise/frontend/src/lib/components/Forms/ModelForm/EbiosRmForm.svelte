<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import * as m from '$paraglide/messages.js';
	import { getOptions } from '$lib/utils/crud';
	import TextArea from '../TextArea.svelte';
	import { page } from '$app/stores';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let context: string;

	let activeActivity: string | null = null;

	$page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		}
	});
</script>

{#if context != 'selectAudit'}
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
		data-focusindex="0"
	/>
{/if}
{#if context !== 'ebiosRmStudy' && context !== 'selectAudit'}
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
		options={getOptions({ objects: model.foreignKeys['folder'] })}
		field="folder"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		hidden={initialData.folder}
	/>
	<AutocompleteSelect
		{form}
		options={getOptions({ objects: model.foreignKeys['reference_entity'] })}
		field="reference_entity"
		cacheLock={cacheLocks['reference_entity']}
		bind:cachedValue={formDataCache['reference_entity']}
		label={m.referenceEntity()}
		hidden={initialData.reference_entity}
	/>
	<AutocompleteSelect
		{form}
		options={getOptions({ objects: model.foreignKeys['risk_matrix'] })}
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
		<TextField
			{form}
			field="ref_id"
			label={m.refId()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<AutocompleteSelect
			{form}
			options={getOptions({ objects: model.foreignKeys['reference_entity'] })}
			field="reference_entity"
			cacheLock={cacheLocks['reference_entity']}
			bind:cachedValue={formDataCache['reference_entity']}
			label={m.referenceEntity()}
			hidden={initialData.reference_entity}
		/>
		<AutocompleteSelect
			multiple
			{form}
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			cacheLock={cacheLocks['authors']}
			bind:cachedValue={formDataCache['authors']}
			label={m.authors()}
		/>
		<AutocompleteSelect
			multiple
			{form}
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
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
			options={getOptions({
				objects: model.foreignKeys['assets'],
				extra_fields: [['folder', 'str']],
				label: 'auto'
			})}
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
{:else}
	<AutocompleteSelect
		multiple
		{form}
		options={getOptions({ objects: model.foreignKeys['compliance_assessments'] })}
		field="compliance_assessments"
		cacheLock={cacheLocks['compliance_assessments']}
		bind:cachedValue={formDataCache['compliance_assessments']}
		label={m.complianceAssessment()}
	/>
{/if}
