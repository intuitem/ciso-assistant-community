<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages';
	import Checkbox from '../Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { page } from '$app/state';
	import FrameworkResultSnippet from '$lib/components/Snippets/AutocompleteSelect/FrameworkResultSnippet.svelte';

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

	let implementationGroupsChoices = $state<{ label: string; value: string }[]>([]);

	let defaultImplementationGroups: string[] = $state([]);

	let is_dynamic = $state(false);

	let isLocked = $derived(form.data?.is_locked || object?.is_locked || false);

	async function handleFrameworkChange(id: string) {
		if (id) {
			await fetch(`/frameworks/${id}`)
				.then((r) => r.json())
				.then((r) => {
					is_dynamic = r['is_dynamic'] || false;
					const implementation_groups = r['implementation_groups_definition'] || [];
					implementationGroupsChoices = implementation_groups.map((group) => ({
						label: group.name,
						value: group.ref_id
					}));
					suggestions = r['reference_controls'].length > 0;

					defaultImplementationGroups = implementation_groups
						.filter((group) => group.default_selected)
						.map((group) => group.ref_id);

					// Only apply defaults when creating a new assessment, not when editing
					if (!object.id) {
						form.form.update((currentData) => {
							return {
								...currentData,
								selected_implementation_groups: defaultImplementationGroups
							};
						});
					}
				});
		}
	}
</script>

{#if (context === 'fromBaseline' || context === 'clone') && initialData.baseline}
	<AutocompleteSelect
		{form}
		field="baseline"
		cacheLock={cacheLocks['baseline']}
		bind:cachedValue={formDataCache['baseline']}
		label={m.baseline()}
		optionsEndpoint="compliance-assessments"
		hidden
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
	hidden={initialData.perimeter && context !== 'clone'}
/>
{#if context === 'fromBaseline' && initialData.baseline}
	<AutocompleteSelect
		{form}
		disabled={object.id}
		optionsEndpoint="compliance-assessments/{page.params.id}/frameworks"
		field="framework"
		cacheLock={cacheLocks['framework']}
		optionsLabelField="str"
		optionsValueField="id"
		bind:cachedValue={formDataCache['framework']}
		label={m.targetFramework()}
		onChange={async (e) => handleFrameworkChange(e)}
		mount={async (e) => handleFrameworkChange(e)}
		additionalMultiselectOptions={{
			liOptionClass: 'flex items-center w-full border-t-8 border-b-8 border-transparent'
		}}
		includeAllOptionFields
	>
		{#snippet optionSnippet(option: Record)}
			<FrameworkResultSnippet {option} />
		{/snippet}
	</AutocompleteSelect>
{:else}
	<AutocompleteSelect
		{form}
		disabled={object.id || context === 'clone'}
		optionsEndpoint="frameworks"
		optionsDetailedUrlParameters={context === 'fromBaseline'
			? [['baseline', initialData.baseline]]
			: []}
		field="framework"
		cacheLock={cacheLocks['framework']}
		bind:cachedValue={formDataCache['framework']}
		label={context === 'clone' ? m.framework() : m.targetFramework()}
		onChange={async (e) => handleFrameworkChange(e)}
		mount={async (e) => handleFrameworkChange(e)}
	/>
{/if}
{#if implementationGroupsChoices.length > 0 && !is_dynamic}
	{#key implementationGroupsChoices}
		<AutocompleteSelect
			multiple
			translateOptions={false}
			{form}
			options={implementationGroupsChoices}
			field="selected_implementation_groups"
			cacheLock={cacheLocks['selected_implementation_groups']}
			bind:cachedValue={formDataCache['selected_implementation_groups']}
			label={m.selectedImplementationGroups()}
		/>
	{/key}
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
	{form}
	field="version"
	label={m.version()}
	helpText={m.versionHelpText()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
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
	<TextField
		{form}
		field="ref_id"
		label={m.refId()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="assets"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
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
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="evidences"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
		field="evidences"
		label={m.evidences()}
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
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	{#if !page.data.user.is_third_party}
		<Checkbox
			{form}
			field="is_locked"
			label={m.isLocked()}
			helpText={m.isLockedHelpText()}
			cacheLock={cacheLocks['is_locked']}
			bind:cachedValue={formDataCache['is_locked']}
		/>
	{/if}
</Dropdown>
