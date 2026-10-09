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
		object?: Record<string, unknown>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {},
		object = {}
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

	// Derived metric: a formula over objects (datasets, edited structurally)
	// or over other metrics (inputs, period by period), one CEL expression,
	// and a preview that evaluates it against a domain without writing.
	import DatasetEditor from '$lib/components/Metrology/DatasetEditor.svelte';
	import type { ReadableModel } from '$lib/components/Metrology/DatasetEditor.svelte';
	import MetricInputsEditor from '$lib/components/Metrology/MetricInputsEditor.svelte';
	import CelInput from '$lib/components/Cel/CelInput.svelte';
	import type { DefinitionOption } from '$lib/components/Metrology/MetricInputsEditor.svelte';
	import {
		datasetReferences,
		foldersWithSeveral,
		formulaKind,
		formulaScope,
		inputReferences,
		type MetricInput
	} from '$lib/utils/derived-metrics';
	import { onMount } from 'svelte';

	const { value: datasetsValue } = formFieldProxy(form, 'datasets');
	const { value: inputsValue } = formFieldProxy(form, 'inputs');
	const { value: expressionValue } = formFieldProxy(form, 'expression');
	const { value: folderValue } = formFieldProxy(form, 'folder');
	let formulaOpen = $state(false);
	let models = $state<ReadableModel[]>([]);
	let definitions = $state<DefinitionOption[]>([]);
	let kind = $state<'objects' | 'metrics'>('objects');
	let kindSettled = false;
	const FREQUENCIES = [
		['realtime', () => m.realTimeContinuous()],
		['hourly', () => m.hourly()],
		['daily', () => m.daily()],
		['weekly', () => m.weekly()],
		['monthly', () => m.monthly()],
		['quarterly', () => m.quarterly()],
		['yearly', () => m.yearly()]
	] as const;
	let previewFrequency = $state('monthly');
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
			// Inputs are quantitative metrics, never this one.
			const res = await fetch('/metric-definitions?category=quantitative&limit=1000');
			if (res.ok) {
				const body = await res.json();
				const rows = Array.isArray(body) ? body : (body.results ?? []);
				definitions = rows
					.filter((row: { id: string }) => row.id !== object?.id)
					.map((row: { id: string; name?: string; str?: string; urn?: string | null }) => ({
						id: row.id,
						name: row.name ?? row.str ?? row.id,
						urn: row.urn
					}));
			}
		} catch {
			definitions = [];
		}
		try {
			const res = await fetch('/folders?content_type=DO&content_type=GL');
			if (res.ok) {
				const body = await res.json();
				const rows = Array.isArray(body) ? body : (body.results ?? []);
				domains = rows.map((row: { id: string; str?: string; name?: string }) => ({
					id: row.id,
					str: row.str ?? row.name ?? ''
				}));
			}
		} catch {
			domains = [];
		}
	});
	$effect(() => {
		if ($datasetsValue && typeof $datasetsValue === 'object' && Object.keys($datasetsValue).length)
			formulaOpen = true;
		if (Array.isArray($inputsValue) && $inputsValue.length) formulaOpen = true;
		if ($expressionValue) formulaOpen = true;
		// The stored formula decides the kind once; the author decides after.
		if (!kindSettled) {
			kind = formulaKind($inputsValue);
			kindSettled = true;
		}
	});
	// A formula reads objects or other metrics, never both: switching drops
	// the other side.
	function setKind(next: 'objects' | 'metrics') {
		kind = next;
		if (next === 'metrics') $datasetsValue = null;
		else $inputsValue = null;
		preview = null;
	}
	$effect(() => {
		if (!previewFolder && $folderValue) previewFolder = $folderValue as string;
	});
	function clearFormula() {
		$datasetsValue = null;
		$inputsValue = null;
		$expressionValue = '';
		preview = null;
	}
	const references = $derived(
		kind === 'metrics'
			? inputReferences($inputsValue)
			: datasetReferences($datasetsValue as Record<string, unknown>)
	);
	function insertReference(ref: string) {
		const current = ($expressionValue as string) ?? '';
		$expressionValue = current && !current.endsWith(' ') ? `${current} ${ref}` : `${current}${ref}`;
	}

	let previewBusy = $state(false);
	let preview = $state<null | {
		ok: boolean;
		value?: unknown;
		datasets?: Record<string, unknown>;
		periods?: {
			start: string;
			value: unknown;
			skipped: boolean;
			inputs?: Record<string, unknown>;
		}[];
		inputs?: Record<string, { id: string; name: string; folder: string }[]>;
		errors?: { code: string; message: string }[];
	}>(null);
	// What the expression editor completes: the inputs or the datasets, with
	// what the last preview answered for each.
	const celScope = $derived(
		formulaScope(kind, $datasetsValue as Record<string, unknown> | null, $inputsValue, preview)
	);
	// The most recent periods first, as a reader scans a series.
	const previewPeriods = $derived([...(preview?.periods ?? [])].reverse().slice(0, 12));
	// Only the latest run may answer: an earlier one finishing late must not
	// overwrite it.
	let previewSeq = 0;
	async function runPreview() {
		const seq = ++previewSeq;
		previewBusy = true;
		try {
			const res = await fetch('/fe-api/metrology/preview-formula', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(
					kind === 'metrics'
						? {
								folder: previewFolder || $folderValue,
								inputs: $inputsValue as MetricInput[],
								expression: $expressionValue,
								frequency: previewFrequency,
								category: data?.category,
								choices_definition: data?.choices_definition,
								definition: object?.id
							}
						: {
								folder: previewFolder || $folderValue,
								datasets: $datasetsValue,
								expression: $expressionValue
							}
				)
			});
			const body = await res.json();
			if (seq === previewSeq) preview = body;
		} catch {
			if (seq === previewSeq)
				preview = { ok: false, errors: [{ code: 'network', message: m.previewFailed() }] };
		} finally {
			if (seq === previewSeq) previewBusy = false;
		}
	}

	// The preview follows the formula: any change to what it reads, where it
	// is tried or how often re-runs it, once the author pauses.
	const previewKey = $derived(
		JSON.stringify([
			kind,
			previewFolder || $folderValue,
			previewFrequency,
			$expressionValue,
			kind === 'metrics' ? $inputsValue : $datasetsValue
		])
	);
	$effect(() => {
		void previewKey;
		if (!formulaOpen || !$expressionValue || !(previewFolder || $folderValue)) return;
		const timer = setTimeout(runPreview, 900);
		return () => clearTimeout(timer);
	});
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
		<div class="flex flex-col gap-1" role="radiogroup" aria-label={m.formulaReads()}>
			<span class="text-sm font-semibold">{m.formulaReads()}</span>
			<div class="flex flex-wrap gap-4 text-sm">
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="radio"
						class="radio"
						name="formula-kind"
						checked={kind === 'objects'}
						onchange={() => setKind('objects')}
						data-testid="formula-kind-objects"
					/>
					{m.formulaFromObjects()}
				</label>
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="radio"
						class="radio"
						name="formula-kind"
						checked={kind === 'metrics'}
						onchange={() => setKind('metrics')}
						data-testid="formula-kind-metrics"
					/>
					{m.formulaFromMetrics()}
				</label>
			</div>
		</div>
		{#if kind === 'metrics'}
			<div class="flex flex-col gap-1">
				<span class="text-sm font-semibold">{m.metricInputs()}</span>
				<span class="text-xs text-surface-500">{m.metricInputsHelpText()}</span>
				<MetricInputsEditor bind:value={$inputsValue} {definitions} {form} self={object} />
			</div>
		{:else}
			<div class="flex flex-col gap-1">
				<span class="text-sm font-semibold">{m.datasets()}</span>
				<span class="text-xs text-surface-500">{m.datasetsHelpText()}</span>
				<DatasetEditor bind:value={$datasetsValue} {models} />
			</div>
		{/if}
		<!-- Not a <label>: a label forwards any click inside it to its first
		     labelable descendant, here the first reference chip, which then
		     inserts that name. -->
		<div class="flex flex-col gap-1" role="group" aria-labelledby="derived-expression-label">
			<span id="derived-expression-label" class="text-sm font-semibold">{m.expression()}</span>
			{#if references.length}
				<div class="flex flex-wrap items-center gap-1.5">
					<span class="text-xs text-surface-500">{m.clickToInsert()}</span>
					{#each references as ref (ref)}
						<button
							type="button"
							class="chip preset-outlined-primary-500 text-primary-700-300 hover:preset-filled-primary-500 cursor-pointer gap-1 px-2 py-0.5 text-xs font-mono transition-colors"
							title={m.insertReference()}
							aria-label={`${m.insertReference()}: ${ref}`}
							onclick={() => insertReference(ref)}
							data-testid="expression-reference"
						>
							<i class="fa-solid fa-plus text-[10px]" aria-hidden="true"></i>{ref}
						</button>
					{/each}
				</div>
			{/if}
			<CelInput
				bind:value={
					() => ($expressionValue as string | undefined) ?? '', (next) => ($expressionValue = next)
				}
				scope={celScope}
				testid="form-input-expression"
				placeholder={kind === 'metrics'
					? 'clicks * 100.0 / trained'
					: 'active.count * 100.0 / controls.count'}
			/>
			<span class="text-xs text-surface-500"
				>{kind === 'metrics' ? m.metricExpressionHelpText() : m.expressionHelpText()}</span
			>
		</div>
		<!-- A workbench beside the form, not part of it: nothing here is saved. -->
		<section
			class="rounded-container border border-dashed border-surface-300-700 bg-surface-100-900 p-3 flex flex-col gap-2"
			aria-label={m.tryFormula()}
			data-testid="formula-preview"
		>
			<header class="flex items-center gap-2">
				<i class="fa-solid fa-flask text-primary-500" aria-hidden="true"></i>
				<span class="text-sm font-semibold">{m.tryFormula()}</span>
				{#if previewBusy}
					<i class="fa-solid fa-spinner fa-spin text-xs text-surface-500" aria-hidden="true"></i>
				{/if}
			</header>
			<p class="text-xs text-surface-500">{m.previewOnlyHint()}</p>
			<div class="flex items-center gap-2 flex-wrap text-xs">
				<span>{m.tryOn()}</span>
				<select
					class="select preset-tonal text-xs w-auto py-0.5"
					bind:value={previewFolder}
					aria-label={m.previewDomain()}
					data-testid="preview-domain"
				>
					{#if !domains.length}
						<option value={$folderValue}>{m.previewDomain()}</option>
					{/if}
					{#each domains as domain (domain.id)}
						<option value={domain.id}>{domain.str}</option>
					{/each}
				</select>
				{#if kind === 'metrics'}
					<span class="text-surface-500">·</span>
					<select
						class="select preset-tonal text-xs w-auto py-0.5"
						bind:value={previewFrequency}
						aria-label={m.previewFrequency()}
						data-testid="preview-frequency"
					>
						{#each FREQUENCIES as [value, label] (value)}
							<option {value}>{label()}</option>
						{/each}
					</select>
				{/if}
				<button
					type="button"
					class="btn btn-sm preset-tonal text-xs ml-auto"
					disabled={previewBusy || !(previewFolder || $folderValue) || !$expressionValue}
					onclick={runPreview}
					data-testid="preview-run"
				>
					<i class="fa-solid fa-rotate-right mr-1" aria-hidden="true"></i>{m.runAgain()}
				</button>
			</div>
			{#if preview}
				{#if preview.ok && preview.periods}
					<div class="text-xs rounded-base bg-surface-50-950 p-2 flex flex-col gap-2">
						<div class="flex flex-col gap-0.5">
							<span class="font-semibold">{m.resolvedInputs()}</span>
							{#each Object.entries(preview.inputs ?? {}) as [key, instances] (key)}
								<div>
									<span class="font-mono">{key}</span>:
									{#if instances.length}
										{instances.map((i) => `${i.name} (${i.folder})`).join(', ')}
										{#each foldersWithSeveral(instances) as folderName (folderName)}
											<span
												class="block text-warning-600-400"
												data-testid="preview-several-instances"
											>
												<i class="fa-solid fa-triangle-exclamation mr-1" aria-hidden="true"></i>
												{m.severalInstancesInFolder({ folder: folderName })}
											</span>
										{/each}
									{:else}
										<span class="text-surface-500">{m.noInstanceResolved()}</span>
									{/if}
								</div>
							{/each}
						</div>
						{#if previewPeriods.length}
							<table class="w-full" data-testid="preview-periods">
								<thead>
									<tr class="text-left text-surface-500">
										<th class="font-normal pr-4">{m.previewPeriod()}</th>
										<th class="font-normal">{m.previewResult()}</th>
									</tr>
								</thead>
								<tbody>
									{#each previewPeriods as period (period.start)}
										<tr>
											<td class="font-mono pr-4">{period.start.slice(0, 16).replace('T', ' ')}</td>
											<td class="font-mono">
												{#if period.skipped}
													<span class="text-surface-500">{m.previewSkipped()}</span>
												{:else}
													{JSON.stringify(period.value)}
												{/if}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						{:else}
							<span class="text-surface-500">{m.previewNoPeriods()}</span>
						{/if}
					</div>
				{:else if preview.ok}
					<div class="text-xs rounded-base bg-surface-50-950 p-2">
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
		</section>
	{/if}
</div>
