<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import Checkbox from '../Checkbox.svelte';

	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		context: string;
	}

	let {
		form,
		model = $bindable(),
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context
	}: Props = $props();

	let suggestions = $state(false);

	async function handleFrameworkChange(id: string) {
		if (id) {
			await fetch(`/frameworks/${id}`)
				.then((r) => r.json())
				.then((r) => {
					const implementation_groups = r['implementation_groups_definition'] || [];
					model.selectOptions['selected_implementation_groups'] = implementation_groups.map(
						(group) => ({ label: group.name, value: group.ref_id })
					);
					suggestions = r['reference_controls'].length > 0;
				});
		}
	}
</script>

{#if context === 'fromBaseline' && initialData.baseline}
	<AutocompleteSelect
		{form}
		field="baseline"
		cacheLock={cacheLocks['baseline']}
		bind:cachedValue={formDataCache['baseline']}
		label={m.baseline()}
		optionsEndpoint="compliance-assessments"
	/>
{/if}
{#if initialData.ebios_rm_studies}
	<AutocompleteSelect
		{form}
		field="ebios_rm_studies"
		multiple
		cacheLock={cacheLocks['ebios_rm_studies']}
		bind:cachedValue={formDataCache['ebios_rm_studies']}
		label={m.ebiosRmStudies()}
		hidden
	/>
{/if}
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
<AutocompleteSelect
	{form}
	disabled={object.id}
	optionsEndpoint="frameworks"
	optionsDetailedUrlParameters={[['baseline', initialData.baseline]]}
	field="framework"
	cacheLock={cacheLocks['framework']}
	bind:cachedValue={formDataCache['framework']}
	label={m.targetFramework()}
	on:change={async (e) => handleFrameworkChange(e.detail)}
	on:mount={async (e) => handleFrameworkChange(e.detail)}
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
<TextField
	type="date"
	{form}
	field="eta"
	label={m.eta()}
	helpText={m.etaHelpText()}
	cacheLock={cacheLocks['eta']}
	bind:cachedValue={formDataCache['eta']}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	{#if context === 'create' && suggestions}
		<Checkbox
			{form}
			field="create_applied_controls_from_suggestions"
			label={m.suggestControls()}
			helpText={m.createAppliedControlsFromSuggestionsHelpText()}
			cacheLock={cacheLocks['create_applied_controls_from_suggestions']}
			bind:cachedValue={formDataCache['create_applied_controls_from_suggestions']}
		/>
	{/if}
	<Checkbox
		{form}
		field="show_documentation_score"
		label={m.useDocumentationScore()}
		helpText={m.useDocumentationScoreHelpText()}
		cacheLock={cacheLocks['show_documentation_score']}
		bind:cachedValue={formDataCache['show_documentation_score']}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="assets"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
		field="assets"
		label={m.assets()}
	/>
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
</Dropdown>
