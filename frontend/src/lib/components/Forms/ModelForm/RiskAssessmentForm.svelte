<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>; // export let context: string = 'default';
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();
	
	// export let updated_fields: Set<string> = new Set();
</script>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

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
<TextField
	{form}
	field="version"
	label={m.version()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
{#if !duplicate}
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
		optionsEndpoint="risk-matrices"
		field="risk_matrix"
		cacheLock={cacheLocks['risk_matrix']}
		bind:cachedValue={formDataCache['risk_matrix']}
		label={m.riskMatrix()}
		helpText={m.riskAssessmentMatrixHelpText()}
		hidden={initialData.risk_matrix}
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
	{#if initialData.ebios_rm_study}
		<AutocompleteSelect
			{form}
			field="ebios_rm_study"
			cacheLock={cacheLocks['ebios_rm_study']}
			bind:cachedValue={formDataCache['ebios_rm_study']}
			label={m.ebiosRmStudy()}
			hidden
		/>
	{/if}
{/if}
