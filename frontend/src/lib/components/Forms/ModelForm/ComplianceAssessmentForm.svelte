<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import Checkbox from '../Checkbox.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: any = {};
	export let context: string;
</script>

{#if context === 'fromBaseline' && initialData.baseline}
	<AutocompleteSelect
		{form}
		field="baseline"
		cacheLock={cacheLocks['baseline']}
		bind:cachedValue={formDataCache['baseline']}
		label={m.baseline()}
		options={getOptions({ objects: model.foreignKeys['baseline'] })}
	/>
{/if}
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
	disabled={object.id}
	options={getOptions({ objects: model.foreignKeys['framework'] })}
	field="framework"
	cacheLock={cacheLocks['framework']}
	bind:cachedValue={formDataCache['framework']}
	label={m.framework()}
	on:change={async (e) => {
		if (e.detail) {
			await fetch(`/frameworks/${e.detail}`)
				.then((r) => r.json())
				.then((r) => {
					const implementation_groups = r['implementation_groups_definition'] || [];
					model.selectOptions['selected_implementation_groups'] = implementation_groups.map(
						(group) => ({ label: group.name, value: group.ref_id })
					);
				});
		}
	}}
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
{#if context === 'create'}
	<Checkbox
		{form}
		field="create_applied_controls_from_suggestions"
		label={m.suggestControls()}
		helpText={m.createAppliedControlsFromSuggestionsHelpText()}
		cacheLock={cacheLocks['create_applied_controls_from_suggestions']}
		bind:cachedValue={formDataCache['create_applied_controls_from_suggestions']}
	/>
{/if}
