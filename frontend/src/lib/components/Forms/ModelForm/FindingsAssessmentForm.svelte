<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import Select from '../Select.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { m } from '$paraglide/messages';
	import Checkbox from '../Checkbox.svelte';

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

	let isLocked = $derived(form.data?.is_locked || object?.is_locked || false);
</script>

<TextField
	{form}
	field="version"
	label={m.version()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
<Select
	{form}
	options={model.selectOptions['category']}
	field="category"
	hide
	label={m.category()}
	cacheLock={cacheLocks['category']}
	bind:cachedValue={formDataCache['category']}
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
	<MarkdownField
		{form}
		field="objectives"
		label={m.objectives()}
		helpText={m.findingsAssessmentObjectivesHelpText()}
		cacheLock={cacheLocks['objectives']}
		bind:cachedValue={formDataCache['objectives']}
	/>
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
	<TextField
		type="date"
		{form}
		field="reported_at"
		label={m.reportedAt()}
		helpText={m.reportedAtHelpText()}
		cacheLock={cacheLocks['reported_at']}
		bind:cachedValue={formDataCache['reported_at']}
	/>
	<NumberField
		{form}
		field="budget"
		label={m.budget()}
		min={0}
		step={0.01}
		cacheLock={cacheLocks['budget']}
		bind:cachedValue={formDataCache['budget']}
	/>
	<NumberField
		{form}
		field="expenses"
		label={m.expenses()}
		helpText={m.expensesHelpText()}
		min={0}
		step={0.01}
		cacheLock={cacheLocks['expenses']}
		bind:cachedValue={formDataCache['expenses']}
	/>
	<TextField
		{form}
		field="reference_link"
		label={m.referenceLink()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['reference_link']}
		bind:cachedValue={formDataCache['reference_link']}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	<AutocompleteSelect
		multiple
		{form}
		createFromSelection={true}
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		translateOptions={false}
		field="filtering_labels"
		helpText={m.labelsHelpText()}
		label={m.labels()}
		allowUserOptions="append"
	/>
	<Checkbox
		{form}
		field="is_locked"
		label={m.isLocked()}
		helpText={m.isLockedHelpText()}
		cacheLock={cacheLocks['is_locked']}
		bind:cachedValue={formDataCache['is_locked']}
	/>
</Dropdown>
