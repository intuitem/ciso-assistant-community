<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
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
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="frameworks"
	field="framework"
	label={m.framework()}
	cacheLock={cacheLocks['framework']}
	bind:cachedValue={formDataCache['framework']}
	disabled={object.id}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="assets"
	label={m.assets()}
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
/>
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
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<TextField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
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
		multiple
		optionsEndpoint="actors"
		optionsLabelField="str"
		optionsInfoFields={{
			fields: [{ field: 'type', translate: true }],
			position: 'prefix'
		}}
		field="reviewers"
		cacheLock={cacheLocks['reviewers']}
		bind:cachedValue={formDataCache['reviewers']}
		label={m.reviewers()}
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
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
</Dropdown>
