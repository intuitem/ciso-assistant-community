<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let riskAssessmentDuplication: boolean = false;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: Record<string, any> = {};
	export let context: string = 'default';
	export let updated_fields: Set<string> = new Set();
</script>

{#if model.urlModel === 'risk-assessments' || model.urlModel === 'risk-assessment-duplicate'}
	<AutocompleteSelect
		{form}
		options={getOptions({
			objects: model.foreignKeys['project'],
			extra_fields: [['folder', 'str']]
		})}
		field="project"
		cacheLock={cacheLocks['project']}
		bind:cachedValue={formDataCache['project']}
		label={m.project()}
		hidden={initialData.project}
	/>
	<TextField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
	{#if !riskAssessmentDuplication}
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			hide
			label={m.status()}
			cacheLock={cacheLocks['status']}
			bind:cachedValue={formDataCache['status']}
		/>
		<AutocompleteSelect
			{form}
			disabled={object.id}
			options={getOptions({ objects: model.foreignKeys['risk_matrix'] })}
			field="risk_matrix"
			cacheLock={cacheLocks['risk_matrix']}
			bind:cachedValue={formDataCache['risk_matrix']}
			label={m.riskMatrix()}
			helpText={m.riskAssessmentMatrixHelpText()}
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
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
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
		<TextArea
			{form}
			field="observation"
			label={m.observation()}
			cacheLock={cacheLocks['observation']}
			bind:cachedValue={formDataCache['observation']}
		/>
	{/if}
{/if}
