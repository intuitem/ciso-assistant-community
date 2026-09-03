<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import { formFieldProxy } from 'sveltekit-superforms';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
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

	const { value: kindValue } = formFieldProxy(form as any, 'kind');
	// Derived, not captured: ModelForm reuses this component with fresh `initialData`,
	// and a stale kind renders the wrong target selector.
	const presetKind = $derived(initialData.kind);
	if (presetKind) kindValue.set(presetKind);
	const kind = $derived(presetKind || $kindValue || 'internal');

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
{#if kind === 'third_party'}
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="entities"
		optionsExtraFields={[['folder', 'str']]}
		field="entities"
		cacheLock={cacheLocks['entities']}
		bind:cachedValue={formDataCache['entities']}
		label={m.thirdParties()}
	/>
{:else}
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="perimeters"
		optionsExtraFields={[['folder', 'str']]}
		field="perimeters"
		cacheLock={cacheLocks['perimeters']}
		bind:cachedValue={formDataCache['perimeters']}
		label={m.perimeters()}
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
