<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import HiddenInput from '../HiddenInput.svelte';
	import TextField from '#lib/components/Forms/TextField.svelte';
	import NumberField from '#lib/components/Forms/NumberField.svelte';
	import Select from '../Select.svelte';
	import SegmentedControl from '../SegmentedControl.svelte';
	import OrderedEntryList from '#lib/components/OrderedEntryList.svelte';
	import type { SuperForm, SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '#lib/utils/types.js';
	import { m } from '#paraglide/messages.js';
	import { directionOf, higherIsBetterFor, type Direction } from '#lib/utils/metrics.js';

	import Dropdown from '#lib/components/Dropdown/Dropdown.svelte';
	import InputChoicesEditor from '#lib/components/Metrology/InputChoicesEditor.svelte';
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
	const { value: nameValue } = formFieldProxy(form, 'name');
	const { value: statusValue } = formFieldProxy(form, 'status');
	const { value: frequencyValue } = formFieldProxy(form, 'collection_frequency');
	const { value: targetValue } = formFieldProxy(form, 'target_value');
	const { value: inlineDefinition } = formFieldProxy(form, 'definition');
	const { value: inlineCategory } = formFieldProxy(form, 'definition.category');
	const { value: inlineDirection } = formFieldProxy(form, 'definition.higher_is_better');
	const { value: inlineChoices } = formFieldProxy(form, 'definition.choices_definition');
	const { value: inlineDefaultTarget } = formFieldProxy(form, 'definition.default_target');
	const { value: inlineDefaultFrequency } = formFieldProxy(
		form,
		'definition.default_collection_frequency'
	);

	// ---------- one step: the definition is written with the metric ----------
	const isCreate = !object?.id;
	// 'define': the form holds the definition's fields; 'existing': a
	// definition is picked and its settings are copied.
	let mode = $state<'define' | 'existing'>(
		initialData.metric_definition || data?.metric_definition ? 'existing' : 'define'
	);

	const modeOptions = $derived([
		{ value: 'define', label: m.defineMetricHere() },
		{ value: 'existing', label: m.useExistingDefinition() }
	]);
	const kindOptions = $derived([
		{ value: 'quantitative', label: m.number() },
		{ value: 'qualitative', label: m.level() }
	]);
	const directionOptions = $derived([
		{ value: 'none', label: m.noDirection() },
		{ value: 'higher', label: m.higherIsBetter() },
		{ value: 'lower', label: m.lowerIsBetter() }
	]);

	let direction = $state<Direction>('none');
	let levels = $state<Array<{ ref_id: string; name: string }>>([]);

	function setMode(next: 'define' | 'existing') {
		mode = next;
		if (next === 'define') {
			$definitionValue = null;
			if (!$inlineDefinition || typeof $inlineDefinition !== 'object') {
				$inlineDefinition = {
					category: 'quantitative',
					unit: null,
					decimals: null,
					higher_is_better: null,
					choices_definition: null,
					default_target: null,
					default_collection_frequency: $frequencyValue ?? null
				};
			}
		} else {
			$inlineDefinition = null;
		}
	}

	if (isCreate) {
		if (!$statusValue || $statusValue === 'draft') $statusValue = 'active';
		if (!$frequencyValue) $frequencyValue = 'monthly';
		setMode(mode);
	}

	// Definition defaults follow the metric's own target and frequency: the
	// definition created here is this metric's, and later metrics from it
	// start the same way.
	$effect(() => {
		if (!isCreate || mode !== 'define') return;
		$inlineDefaultFrequency = $frequencyValue ?? null;
		$inlineDefaultTarget = $targetValue === '' || $targetValue === undefined ? null : $targetValue;
	});
	$effect(() => {
		if (!isCreate || mode !== 'define') return;
		$inlineDirection = higherIsBetterFor(direction);
	});
	$effect(() => {
		if (!isCreate || mode !== 'define') return;
		$inlineChoices = $inlineCategory === 'qualitative' ? levels : null;
	});
	const isLevel = $derived(mode === 'define' && $inlineCategory === 'qualitative');

	// ---------- the similar-name hint ----------
	type Similar = {
		id: string;
		name: string;
		folder: { id: string; name: string };
		category: string;
		domains: string[];
	};
	let similar = $state<Similar | null>(null);
	let dismissedFor = $state('');
	let lookup = 0;
	$effect(() => {
		// Every change outdates a lookup in flight, even one that ends the hint.
		const run = ++lookup;
		if (!isCreate || mode !== 'define') {
			similar = null;
			return;
		}
		const name = String($nameValue ?? '').trim();
		const category = String($inlineCategory ?? 'quantitative');
		if (name.length < 3 || name === dismissedFor) {
			similar = null;
			return;
		}
		const timer = setTimeout(async () => {
			try {
				const params = new URLSearchParams({ name, category });
				const res = await fetch(`/fe-api/metrology/similar-definitions?${params}`);
				if (!res.ok || run !== lookup) return;
				const found: Similar[] = await res.json();
				// The name may have changed while the body was read.
				if (run !== lookup) return;
				similar = found[0] ?? null;
			} catch {
				// An older lookup failing must not hide a newer hint.
				if (run === lookup) similar = null;
			}
		}, 300);
		return () => clearTimeout(timer);
	});

	function useSimilar() {
		if (!similar) return;
		const picked = similar;
		setMode('existing');
		$definitionValue = picked.id;
		definitionVersion += 1;
		similar = null;
	}
	function keepMine() {
		dismissedFor = String($nameValue ?? '').trim();
		similar = null;
	}

	// ---------- from an existing definition: copied settings, suggested name ----------
	// The picked definition, with its unit and defaults: fetched by id, so
	// the picker keeps its plain labels.
	let pickedDefinition = $state<any>(null);
	$effect(() => {
		const id = $definitionValue;
		if (!isCreate || mode !== 'existing' || !id) {
			pickedDefinition = null;
			return;
		}
		let alive = true;
		fetch(`/fe-api/metrology/metric-definitions/${id}`)
			.then((r) => (r.ok ? r.json() : null))
			.then((definition) => {
				if (alive) pickedDefinition = definition;
			})
			.catch(() => {
				if (alive) pickedDefinition = null;
			});
		return () => {
			alive = false;
		};
	});
	let folderName = $state('');
	$effect(() => {
		const folder = $folderValue;
		if (!isCreate || !folder) {
			folderName = '';
			return;
		}
		let alive = true;
		fetch(`/fe-api/folders/${folder}`)
			.then((r) => (r.ok ? r.json() : null))
			.then((f) => {
				if (alive) folderName = f?.name ?? '';
			})
			.catch(() => {});
		return () => {
			alive = false;
		};
	});
	// The suggestion follows the picked definition and the domain until the
	// name is typed by hand.
	let lastSuggestion = $state('');
	$effect(() => {
		if (!isCreate || mode !== 'existing' || !pickedDefinition) return;
		const suggestion = folderName
			? `${pickedDefinition.name} · ${folderName}`
			: pickedDefinition.name;
		const current = String($nameValue ?? '');
		if (!current || current === lastSuggestion) {
			$nameValue = suggestion;
			lastSuggestion = suggestion;
		}
	});
	// Defaults copied once, when the definition is picked.
	let copiedFrom = $state('');
	$effect(() => {
		if (!isCreate || mode !== 'existing' || !pickedDefinition) return;
		if (copiedFrom === pickedDefinition.id) return;
		copiedFrom = pickedDefinition.id;
		if (pickedDefinition.default_collection_frequency) {
			$frequencyValue = pickedDefinition.default_collection_frequency;
		}
		if (pickedDefinition.default_target !== null && pickedDefinition.default_target !== undefined) {
			$targetValue = pickedDefinition.default_target;
		}
	});

	// Editing a computed metric: its formula, shown here and edited in the
	// drawer the metric's page uses, so the formula and its picks have one
	// place to change, whether the formula is the metric's own or its
	// definition's.
	import { onMount, tick } from 'svelte';
	import FormulaDrawer from '#lib/components/Metrology/FormulaDrawer.svelte';
	import type { Composition, Saved } from '#lib/components/Metrology/ComposeMetricEditor.svelte';
	import type { DefinitionComposition } from '#lib/components/Metrology/DefinitionFormulaPanel.svelte';

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

{#if isCreate && similar}
	<div
		role="status"
		class="flex items-center gap-3 rounded-base border border-primary-200 bg-primary-50 dark:bg-primary-950 dark:border-primary-800 px-3 py-2 text-sm"
		data-testid="similar-definition-hint"
	>
		<i class="fa-solid fa-magnifying-glass text-primary-500" aria-hidden="true"></i>
		<p class="flex-1 m-0">
			{m.similarDefinitionExists({
				name: similar.name,
				folder: similar.folder.name
			})}{#if similar.domains.length}{' · '}{m.measuredIn({
					domains: similar.domains.join(', ')
				})}{/if}
		</p>
		<button type="button" class="btn btn-sm preset-filled-primary-500" onclick={useSimilar}>
			{m.useIt()}
		</button>
		<button type="button" class="btn btn-sm preset-tonal" onclick={keepMine}>
			{m.keepMine()}
		</button>
	</div>
{/if}

{#if isCreate && !initialData.metric_definition}
	<div class="form-group">
		<SegmentedControl
			options={modeOptions}
			value={mode}
			onChange={(value) => setMode(value as 'define' | 'existing')}
			ariaLabel={m.metricDefinition()}
		/>
		{#if mode === 'define'}
			<p class="text-xs text-surface-500 mt-1">{m.oneStepMetricHelpText()}</p>
		{/if}
	</div>
{/if}

{#if isCreate && mode === 'define'}
	<div class="grid grid-cols-[auto_minmax(0,1fr)] gap-4 items-start">
		<div class="form-group">
			<span class="text-sm font-semibold block mb-1">{m.kind()}</span>
			<SegmentedControl
				options={kindOptions}
				value={String($inlineCategory ?? 'quantitative')}
				onChange={(value) => ($inlineCategory = value)}
				ariaLabel={m.kind()}
			/>
		</div>
		{#if isLevel}
			<div class="form-group">
				<span class="text-sm font-semibold mb-1 block">{m.choicesDefinition()}</span>
				<OrderedEntryList bind:entries={levels} onchange={(entries) => (levels = entries)} />
			</div>
		{:else}
			<div class="grid grid-cols-[minmax(0,1fr)_8rem] gap-4">
				<AutocompleteSelect
					{form}
					optionsEndpoint="terminologies?field_path=metric_definition.unit&is_visible=true"
					optionsLabelField="translated_name"
					field="definition.unit"
					label={m.unit()}
					cacheLock={cacheLocks['definition.unit']}
					bind:cachedValue={formDataCache['definition.unit']}
				/>
				<NumberField {form} field="definition.decimals" label={m.decimals()} min={0} max={6} />
			</div>
		{/if}
	</div>
	{#if !isLevel}
		<p class="text-xs text-surface-500 -mt-2">{m.decimalsHelpText()}</p>
	{/if}
	<div class="form-group">
		<span class="text-sm font-semibold block mb-1">{m.direction()}</span>
		<SegmentedControl
			options={directionOptions}
			value={direction}
			onChange={(value) => (direction = value as Direction)}
			ariaLabel={m.direction()}
		/>
		<p class="text-xs text-surface-500 mt-1">
			{direction === 'none'
				? m.noDirectionHelpText()
				: direction === 'lower'
					? m.lowerIsBetterHelpText()
					: m.higherIsBetterHelpText()}
		</p>
	</div>
{:else}
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
	{#if isCreate && pickedDefinition}
		<div
			class="rounded-base border border-surface-200-800 bg-surface-50-950 p-3 text-sm flex flex-wrap gap-x-6 gap-y-1"
			data-testid="copied-from-definition"
		>
			<span class="w-full text-xs font-semibold text-surface-500">{m.copiedFromDefinition()}</span>
			<span
				><span class="text-surface-500">{m.kind()}:</span>
				{pickedDefinition.category === 'qualitative' ? m.level() : m.number()}</span
			>
			{#if pickedDefinition.unit?.name}
				<span><span class="text-surface-500">{m.unit()}:</span> {pickedDefinition.unit.name}</span>
			{/if}
			<span>
				<span class="text-surface-500">{m.direction()}:</span>
				{directionOf(pickedDefinition) === 'higher'
					? m.higherIsBetter()
					: directionOf(pickedDefinition) === 'lower'
						? m.lowerIsBetter()
						: m.noDirection()}
			</span>
			{#if pickedDefinition.decimals !== null && pickedDefinition.decimals !== undefined}
				<span
					><span class="text-surface-500">{m.decimals()}:</span> {pickedDefinition.decimals}</span
				>
			{/if}
		</div>
	{/if}
	{#if !composition?.composable}
		{#key definitionVersion}
			<InputChoicesEditor
				bind:value={$inputChoices}
				definition={$definitionValue as string | undefined}
				folder={$folderValue as string | undefined}
			/>
		{/key}
	{/if}
{/if}
{#if !isCreate}
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		disableDoubleDash
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
{/if}
<div class="grid grid-cols-2 gap-4">
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
</div>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	lazy
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
<Dropdown open={false} class="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	{#if isCreate}
		<Select
			{form}
			options={model.selectOptions['status']}
			field="status"
			label={m.status()}
			disableDoubleDash
			cacheLock={cacheLocks['status']}
			bind:cachedValue={formDataCache['status']}
		/>
	{/if}
	<AutocompleteSelect
		{form}
		optionsEndpoint="evidences"
		lazy
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
		field="evidences"
		cacheLock={cacheLocks['evidences']}
		bind:cachedValue={formDataCache['evidences']}
		label={m.evidence()}
	/>
	<NumberField
		{form}
		field="collection_grace_days"
		label={m.collectionGraceDays()}
		min={0}
		max={28}
		helpText={m.collectionGraceDaysHelpText()}
	/>
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
