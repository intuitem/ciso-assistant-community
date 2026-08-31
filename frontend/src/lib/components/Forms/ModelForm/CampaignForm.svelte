<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import { page } from '$app/state';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

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

	const formData = form.form;

	// The campaign's audience is preset by the entry point: the general
	// campaigns menu targets internal entities, the third-party one external
	// entities. Immutable once the campaign exists.
	const isEdit = Boolean(object?.id);
	const urlTargetScope = page.url.searchParams.get('target_scope');
	if (!isEdit && (urlTargetScope === 'internal' || urlTargetScope === 'external')) {
		$formData.target_scope = urlTargetScope;
	}
	let targetScope = $derived($formData.target_scope ?? 'internal');

	// Flipping the audience invalidates the current entity selection.
	let previousScope = targetScope;
	$effect(() => {
		if (targetScope !== previousScope) {
			previousScope = targetScope;
			$formData.entities = [];
			formDataCache['entities'] = [];
		}
	});

	let implementationGroupsChoices = $state<
		{ label: string; value: { id: string; framework: string } }[]
	>([]);

	async function handleFrameworkChange(ids: string[]) {
		if (ids) {
			const implementationGroups = await Promise.all(
				ids.map(async (id) => {
					const response = await fetch(`/frameworks/${id}`);
					const data = await response.json();
					const groups = data['implementation_groups_definition'] || [];
					return groups.map((group) => ({ ...group, framework_id: id }));
				})
			);
			implementationGroupsChoices = implementationGroups.flat().map((group) => ({
				label: group.name,
				value: { value: group.ref_id, framework: group.framework_id }
			}));
		} else {
			implementationGroupsChoices = [];
		}
	}
</script>

<Select
	{form}
	options={model.selectOptions['target_scope']}
	field="target_scope"
	label={m.targetScope()}
	disabled={isEdit}
	helpText={m.campaignTargetScopeHelpText()}
	cacheLock={cacheLocks['target_scope']}
	bind:cachedValue={formDataCache['target_scope']}
/>
{#key targetScope}
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="entities"
		optionsDetailedUrlParameters={[['scope', targetScope]]}
		optionsExtraFields={[['folder', 'str']]}
		field="entities"
		cacheLock={cacheLocks['entities']}
		bind:cachedValue={formDataCache['entities']}
		label={m.entities()}
		helpText={targetScope === 'internal'
			? m.campaignInternalEntitiesHelpText()
			: m.campaignExternalEntitiesHelpText()}
	/>
{/key}
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="frameworks"
	field="frameworks"
	cacheLock={cacheLocks['frameworks']}
	bind:cachedValue={formDataCache['frameworks']}
	label={m.targetFrameworks()}
	hidden={initialData.frameworks}
	onChange={async (e) => handleFrameworkChange(e)}
	mount={async (e) => handleFrameworkChange(e)}
/>
{#if implementationGroupsChoices.length > 0 && !initialData.frameworks}
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
{/if}
<TextField
	type="date"
	{form}
	field="start_date"
	label={m.startDate()}
	cacheLock={cacheLocks['start_date']}
	bind:cachedValue={formDataCache['start_date']}
/>
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
