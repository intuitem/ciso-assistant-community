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

	// Derived metric: datasets edited structurally, one CEL expression, and a
	// preview that evaluates the formula against a domain without writing.
	import DatasetEditor from '$lib/components/Metrology/DatasetEditor.svelte';
	import type { ReadableModel } from '$lib/components/Metrology/DatasetEditor.svelte';
	import { datasetReferences } from '$lib/utils/derived-metrics';
	import { onMount } from 'svelte';

	const { value: datasetsValue } = formFieldProxy(form, 'datasets');
	const { value: expressionValue } = formFieldProxy(form, 'expression');
	const { value: folderValue } = formFieldProxy(form, 'folder');
	let formulaOpen = $state(false);
	let models = $state<ReadableModel[]>([]);
	let domains = $state<{ id: string; str: string }[]>([]);
	let previewFolder = $state('');
	onMount(async () => {
		try {
			const res = await fetch('/fe-api/metrology/readable-models');
			if (res.ok) models = await res.json();
		} catch {
			models = [];
		}
		try {
			const res = await fetch('/folders?content_type=DO&content_type=GL');
			if (res.ok) {
				const body = await res.json();
				const rows = Array.isArray(body) ? body : (body.results ?? []);
				domains = rows.map((row: any) => ({ id: row.id, str: row.str ?? row.name }));
			}
		} catch {
			domains = [];
		}
	});
	$effect(() => {
		if ($datasetsValue && typeof $datasetsValue === 'object' && Object.keys($datasetsValue).length)
			formulaOpen = true;
		if ($expressionValue) formulaOpen = true;
	});
	$effect(() => {
		if (!previewFolder && $folderValue) previewFolder = $folderValue as string;
	});
	function clearFormula() {
		$datasetsValue = null;
		$expressionValue = '';
		preview = null;
	}
	const references = $derived(datasetReferences($datasetsValue as Record<string, any>));
	function insertReference(ref: string) {
		const current = ($expressionValue as string) ?? '';
		$expressionValue = current && !current.endsWith(' ') ? `${current} ${ref}` : `${current}${ref}`;
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
					folder: previewFolder || $folderValue,
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
		<input
			type="checkbox"
			class="checkbox"
			checked={formulaOpen}
			onchange={(e) => {
				formulaOpen = e.currentTarget.checked;
				if (!formulaOpen) clearFormula();
			}}
			data-testid="derived-metric-toggle"
		/>
		{m.derivedMetric()}
	</label>
	<p class="text-xs text-surface-500">{m.derivedMetricHelpText()}</p>
	{#if formulaOpen}
		<div class="flex flex-col gap-1">
			<span class="text-sm font-semibold">{m.datasets()}</span>
			<span class="text-xs text-surface-500">{m.datasetsHelpText()}</span>
			<DatasetEditor bind:value={$datasetsValue} {models} />
		</div>
		<label class="flex flex-col gap-1">
			<span class="text-sm font-semibold">{m.expression()}</span>
			{#if references.length}
				<div class="flex flex-wrap gap-1">
					{#each references as ref (ref)}
						<button
							type="button"
							class="chip preset-tonal text-[10px] font-mono"
							onclick={() => insertReference(ref)}
						>
							{ref}
						</button>
					{/each}
				</div>
			{/if}
			<textarea
				class="textarea text-sm font-mono w-full"
				rows="2"
				data-testid="form-input-expression"
				bind:value={$expressionValue}
				placeholder="active.count * 100.0 / controls.count"
			></textarea>
			<span class="text-xs text-surface-500">{m.expressionHelpText()}</span>
		</label>
		<div class="flex items-center gap-2 flex-wrap">
			<select class="select text-xs w-56" bind:value={previewFolder} title={m.previewDomain()}>
				{#if !domains.length}
					<option value={$folderValue}>{m.previewDomain()}</option>
				{/if}
				{#each domains as domain (domain.id)}
					<option value={domain.id}>{domain.str}</option>
				{/each}
			</select>
			<button
				type="button"
				class="btn preset-tonal text-xs"
				disabled={previewBusy || !(previewFolder || $folderValue) || !$expressionValue}
				onclick={runPreview}
			>
				<i class="fa-solid fa-play mr-1"></i>{m.previewFormula()}
			</button>
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
