<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import HiddenInput from '../HiddenInput.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import type { SuperForm, SuperValidated } from 'sveltekit-superforms';
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
		object?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		debug = false,
		object = {}
	}: Props = $props();

	// A metric computed from other metrics: which instances its inputs read
	// when the domain holds several.
	const { value: inputChoices } = formFieldProxy(form, 'input_choices');
	const { value: definitionValue } = formFieldProxy(form, 'metric_definition');
	const { value: folderValue } = formFieldProxy(form, 'folder');

	// Editing a computed metric: its formula, shown here and edited in the
	// drawer the metric's page uses, so the formula and its picks have one
	// place to change, whether the formula is the metric's own or its
	// definition's.
	import { onMount, tick } from 'svelte';
	import FormulaDrawer from '$lib/components/Metrology/FormulaDrawer.svelte';
	import type { Composition, Saved } from '$lib/components/Metrology/ComposeMetricEditor.svelte';
	import type { DefinitionComposition } from '$lib/components/Metrology/DefinitionFormulaPanel.svelte';

	let composition = $state<any>(null);
	async function loadComposition() {
		if (!object?.id) return;
		try {
			const res = await fetch(`/fe-api/metrology/composition/${object.id}`);
			if (res.ok) composition = await res.json();
		} catch {
			composition = null;
		}
	}
	onMount(loadComposition);

	let editedComposition = $state<Composition | DefinitionComposition | null>(null);
	let editFormulaButton = $state<HTMLButtonElement | null>(null);
	// Remounts the definition picker and the input choices on a save: they
	// show a fork's new name, and a changed definition's inputs.
	let definitionVersion = $state(0);

	async function closeFormula() {
		editedComposition = null;
		await tick();
		editFormulaButton?.focus();
	}

	// The save wrote the definition and the picks: this form holds them too,
	// and would write the old ones back. It adopts them, untainted (they are
	// saved already), and keeps whatever else the author was editing.
	async function formulaSaved(saved: Saved) {
		(form as unknown as SuperForm<Record<string, unknown>>).form.update(
			(data: Record<string, unknown>) => ({
				...data,
				...(saved.metric_definition ? { metric_definition: saved.metric_definition } : {}),
				...(saved.input_choices ? { input_choices: saved.input_choices } : {})
			}),
			{ taint: false }
		);
		definitionVersion += 1;
		await loadComposition();
	}
	const formula = $derived((composition?.expression ?? '') as string);

	function editFormula() {
		editedComposition = composition;
	}
</script>

<HiddenInput {form} field="applied_controls" />

{#if formula}
	<div
		class="card bg-surface-100-900 border border-surface-200-800 p-3 flex items-center gap-3"
		data-testid="instance-formula"
	>
		<i class="fa-solid fa-square-root-variable text-primary-500" aria-hidden="true"></i>
		<div class="flex-1 min-w-0">
			<span class="text-xs font-semibold block">{m.formula()}</span>
			<code class="text-xs block truncate" title={formula}>{formula}</code>
		</div>
		<button
			type="button"
			class="btn btn-sm preset-tonal-primary shrink-0"
			onclick={editFormula}
			aria-expanded={!!editedComposition}
			bind:this={editFormulaButton}
			data-testid="instance-edit-formula"
		>
			{m.editFormula()}
		</button>
	</div>
{/if}

{#if object?.id}
	<FormulaDrawer
		instanceId={object.id}
		composition={editedComposition}
		onClose={closeFormula}
		onSaved={formulaSaved}
	/>
{/if}

{#key definitionVersion}
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
{/key}
{#if !composition?.composable}
	{#key definitionVersion}
		<InputChoicesEditor
			bind:value={$inputChoices}
			definition={$definitionValue as string | undefined}
			folder={$folderValue as string | undefined}
		/>
	{/key}
{/if}
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
