<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import InputChoicesEditor from '$lib/components/Metrology/InputChoicesEditor.svelte';
	import { formFieldProxy } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: any;
		debug?: boolean;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		debug = false
	}: Props = $props();

	// A metric computed from other metrics: which instances its inputs read
	// when the domain holds several.
	const { value: inputChoices } = formFieldProxy(form, 'input_choices');
	const { value: definitionValue } = formFieldProxy(form, 'metric_definition');
	const { value: folderValue } = formFieldProxy(form, 'folder');
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="metric-definitions"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	field="metric_definition"
	cacheLock={cacheLocks['metric_definition']}
	bind:cachedValue={formDataCache['metric_definition']}
	label={m.metricDefinition()}
	disabled={!!initialData.metric_definition}
/>
<InputChoicesEditor
	bind:value={$inputChoices}
	definition={$definitionValue as string | undefined}
	folder={$folderValue as string | undefined}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	disableDoubleDash
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<Select
	{form}
	options={model.selectOptions['collection_frequency']}
	field="collection_frequency"
	label={m.collectionFrequency()}
	cacheLock={cacheLocks['collection_frequency']}
	bind:cachedValue={formDataCache['collection_frequency']}
/>
<TextField
	{form}
	type="number"
	field="target_value"
	label={m.targetValue()}
	cacheLock={cacheLocks['target_value']}
	bind:cachedValue={formDataCache['target_value']}
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
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	label={m.owner()}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="evidences"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.evidence()}
/>
<Dropdown open={false} class="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="organisation-objectives"
		optionsLabelField="auto"
		field="organisation_objectives"
		cacheLock={cacheLocks['organisation_objectives']}
		bind:cachedValue={formDataCache['organisation_objectives']}
		label={m.organisationObjectives()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		field="filtering_labels"
		cacheLock={cacheLocks['filtering_labels']}
		bind:cachedValue={formDataCache['filtering_labels']}
		label={m.labels()}
	/>
</Dropdown>
