<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Checkbox from '../Checkbox.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '../Select.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	let implementationGroupsChoices = $state<{ label: string; value: string }[]>([]);
	let frameworkRequestSeq = 0;

	async function handleFrameworkChange(id: string) {
		if (!id) return;
		const seq = ++frameworkRequestSeq;
		let r: any;
		try {
			const res = await fetch(`/frameworks/${id}`);
			if (!res.ok) return;
			r = await res.json();
		} catch {
			return;
		}
		if (seq !== frameworkRequestSeq) return;
		const implementation_groups = r['implementation_groups_definition'] || [];
		implementationGroupsChoices = implementation_groups.map((group: any) => ({
			label: group.name,
			value: group.ref_id
		}));
		const defaults = implementation_groups
			.filter((group: any) => group.default_selected)
			.map((group: any) => group.ref_id);
		if (!object.id) {
			form.form.update((currentData: any) => ({
				...currentData,
				selected_implementation_groups: defaults
			}));
		}
	}
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="frameworks"
	field="framework"
	label={m.framework()}
	cacheLock={cacheLocks['framework']}
	bind:cachedValue={formDataCache['framework']}
	disabled={object.id}
	onChange={async (e) => handleFrameworkChange(e)}
	mount={async (e) => handleFrameworkChange(e)}
/>
{#if implementationGroupsChoices.length > 0}
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
	multiple
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
{#if !object.id}
	<Checkbox
		{form}
		field="create_follow_up_assessment"
		label={m.createFollowUpAssessment()}
		helpText={m.createFollowUpAssessmentHelpText()}
	/>
{/if}
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<NumberField
		{form}
		field="history_depth"
		label={m.historyDepth()}
		helpText={m.historyDepthHelpText()}
		cacheLock={cacheLocks['history_depth']}
		bind:cachedValue={formDataCache['history_depth']}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="findings-assessments"
		optionsExtraFields={[['folder', 'str']]}
		field="follow_up_assessment"
		nullable
		label={m.followUpAssessment()}
		cacheLock={cacheLocks['follow_up_assessment']}
		bind:cachedValue={formDataCache['follow_up_assessment']}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
</Dropdown>
