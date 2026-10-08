<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Select from '../Select.svelte';
	import OrderedEntryList from '$lib/components/OrderedEntryList.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { formFieldProxy } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {}
	}: Props = $props();

	const isQualitative = $derived.by(() => {
		return data?.category === 'qualitative';
	});

	// Handle choices_definition as parsed array
	const { value: choicesDefinitionValue } = formFieldProxy(form, 'choices_definition');

	let choicesEntries = $state<Array<{ ref_id: string; name: string }>>([]);

	// Parse initial value
	$effect(() => {
		if ($choicesDefinitionValue) {
			try {
				if (typeof $choicesDefinitionValue === 'string') {
					choicesEntries = JSON.parse($choicesDefinitionValue);
				} else if (Array.isArray($choicesDefinitionValue)) {
					choicesEntries = $choicesDefinitionValue;
				}
			} catch (e) {
				console.error('Failed to parse choices_definition:', e);
				choicesEntries = [];
			}
		} else {
			choicesEntries = [];
		}
	});

	function handleChoicesChange(entries: Array<{ ref_id: string; name: string }>) {
		$choicesDefinitionValue = entries;
	}

	// Derived metric: datasets (JSON, name -> read configuration) and one CEL
	// expression. The textarea holds the JSON text; the form field holds the
	// parsed object, or the raw text when it does not parse so the backend
	// says so.
	const { value: datasetsValue } = formFieldProxy(form, 'datasets');
	const { value: expressionValue } = formFieldProxy(form, 'expression');
	const { value: folderValue } = formFieldProxy(form, 'folder');
	let datasetsText = $state('');
	let datasetsInvalid = $state(false);
	let formulaOpen = $state(false);
	$effect(() => {
		const current = $datasetsValue;
		if (current && typeof current === 'object') {
			const text = JSON.stringify(current, null, 2);
			if (text !== datasetsText) datasetsText = text;
			formulaOpen = true;
		} else if (typeof current === 'string' && current && !datasetsText) {
			datasetsText = current;
		}
		if ($expressionValue) formulaOpen = true;
	});
	function onDatasetsInput(text: string) {
		datasetsText = text;
		if (!text.trim()) {
			$datasetsValue = null;
			datasetsInvalid = false;
			return;
		}
		try {
			$datasetsValue = JSON.parse(text);
			datasetsInvalid = false;
		} catch {
			$datasetsValue = text;
			datasetsInvalid = true;
		}
	}

	let previewBusy = $state(false);
	let preview = $state<null | {
		ok: boolean;
		value?: unknown;
		datasets?: Record<string, unknown>;
		errors?: { code: string; message: string }[];
	}>(null);
	async function runPreview() {
		previewBusy = true;
		preview = null;
		try {
			const res = await fetch('/fe-api/metrology/preview-formula', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					folder: $folderValue,
					datasets: $datasetsValue,
					expression: $expressionValue
				})
			});
			preview = await res.json();
		} catch {
			preview = { ok: false, errors: [{ code: 'network', message: m.previewFailed() }] };
		} finally {
			previewBusy = false;
		}
	}
</script>

<Select
	{form}
	options={model.selectOptions['category']}
	field="category"
	label={m.category()}
	cacheLock={cacheLocks['category']}
	disableDoubleDash
	bind:cachedValue={formDataCache['category']}
/>
{#if isQualitative}
	<div class="form-group">
		<span class="text-sm font-semibold mb-2 block">{m.choicesDefinition()}</span>
		<OrderedEntryList bind:entries={choicesEntries} onchange={handleChoicesChange} />
	</div>
{:else}
	<AutocompleteSelect
		{form}
		optionsEndpoint="terminologies?field_path=metric_definition.unit&is_visible=true"
		optionsLabelField="translated_name"
		field="unit"
		label={m.unit()}
		cacheLock={cacheLocks['unit']}
		bind:cachedValue={formDataCache['unit']}
	/>
	<TextField
		{form}
		type="number"
		field="default_target"
		label={m.defaultTarget()}
		helpText={m.defaultTargetHelpText()}
		cacheLock={cacheLocks['default_target']}
		bind:cachedValue={formDataCache['default_target']}
	/>
{/if}
<TextField
	{form}
	field="provider"
	label={m.provider()}
	cacheLock={cacheLocks['provider']}
	bind:cachedValue={formDataCache['provider']}
/>
<Checkbox
	{form}
	field="higher_is_better"
	label={m.higherIsBetter()}
	helpText={m.higherIsBetterHelpText()}
	cacheLock={cacheLocks['higher_is_better']}
	bind:cachedValue={formDataCache['higher_is_better']}
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

<div class="form-group rounded-base border border-surface-200-800 p-3 flex flex-col gap-2">
	<label class="flex items-center gap-2 text-sm font-semibold cursor-pointer">
		<input type="checkbox" class="checkbox" bind:checked={formulaOpen} />
		{m.derivedMetric()}
	</label>
	<p class="text-xs text-surface-500">{m.derivedMetricHelpText()}</p>
	{#if formulaOpen}
		<label class="flex flex-col gap-1">
			<span class="text-sm font-semibold">{m.datasets()}</span>
			<textarea
				class="textarea text-xs font-mono w-full"
				rows="8"
				data-testid="form-input-datasets"
				value={datasetsText}
				oninput={(e) => onDatasetsInput(e.currentTarget.value)}
				placeholder={'{"controls": {"model": "applied_control", "aggregates": [{"fn": "count"}]}}'}
			></textarea>
			{#if datasetsInvalid}
				<span class="text-xs text-error-500">{m.datasetsInvalidJson()}</span>
			{/if}
			<span class="text-xs text-surface-500">{m.datasetsHelpText()}</span>
		</label>
		<label class="flex flex-col gap-1">
			<span class="text-sm font-semibold">{m.expression()}</span>
			<textarea
				class="textarea text-sm font-mono w-full"
				rows="2"
				data-testid="form-input-expression"
				bind:value={$expressionValue}
				placeholder="active.count * 100.0 / controls.count"
			></textarea>
			<span class="text-xs text-surface-500">{m.expressionHelpText()}</span>
		</label>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="btn preset-tonal text-xs"
				disabled={previewBusy || !$folderValue || !$expressionValue}
				onclick={runPreview}
			>
				<i class="fa-solid fa-play mr-1"></i>{m.previewFormula()}
			</button>
			{#if !$folderValue}
				<span class="text-xs text-surface-500">{m.previewNeedsFolder()}</span>
			{/if}
		</div>
		{#if preview}
			{#if preview.ok}
				<div class="text-xs rounded-base bg-surface-100-900 p-2">
					<div>
						<span class="font-semibold">{m.previewResult()}:</span>
						<span class="font-mono">{JSON.stringify(preview.value)}</span>
					</div>
					<pre class="font-mono whitespace-pre-wrap mt-1">{JSON.stringify(
							preview.datasets,
							null,
							2
						)}</pre>
				</div>
			{:else}
				<ul class="text-xs text-error-500 list-disc pl-4">
					{#each preview.errors ?? [] as err (err.message)}
						<li>{err.message}</li>
					{/each}
				</ul>
			{/if}
		{/if}
	{/if}
</div>
