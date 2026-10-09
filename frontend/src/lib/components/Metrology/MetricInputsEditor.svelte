<script lang="ts">
	// Editor for a metric formula's inputs: each one names another metric
	// definition and says how its instances in the domain and its sub-domains
	// combine, period by period. The value is the backend's own list.
	import { m } from '$paraglide/messages';
	import {
		COMBINES,
		datasetNameProblem,
		sanitizeDatasetName,
		type Combine,
		type MetricInput
	} from '$lib/utils/derived-metrics';

	export interface DefinitionOption {
		id: string;
		name: string;
		urn?: string | null;
	}

	interface Props {
		// The form field as stored: a list of inputs, or nothing yet.
		value: unknown;
		definitions: DefinitionOption[];
		onchange?: () => void;
	}
	let { value = $bindable(), definitions, onchange }: Props = $props();

	interface Row extends MetricInput {
		keyDraft?: string;
		keyProblem?: 'required' | 'invalid' | 'taken' | null;
	}

	let rows = $state<Row[]>([]);
	let lastEmitted = '';

	$effect(() => {
		const serialized = JSON.stringify(value ?? null);
		if (serialized !== lastEmitted) {
			rows = Array.isArray(value) ? (value as MetricInput[]).map((input) => ({ ...input })) : [];
			lastEmitted = serialized;
		}
	});

	function emit() {
		const next: MetricInput[] = rows.map(({ key, definition, combine }) => ({
			key,
			definition,
			combine
		}));
		lastEmitted = JSON.stringify(next.length ? next : null);
		value = next.length ? next : null;
		onchange?.();
	}

	function uniqueKey(base: string): string {
		const taken = new Set(rows.map((row) => row.key));
		if (!taken.has(base)) return base;
		let index = 2;
		while (taken.has(`${base}_${index}`)) index += 1;
		return `${base}_${index}`;
	}

	function addInput() {
		rows.push({ key: uniqueKey('input'), definition: '', combine: 'one' });
		emit();
	}

	function removeInput(index: number) {
		rows.splice(index, 1);
		emit();
	}

	function setKey(row: Row, raw: string) {
		const key = sanitizeDatasetName(raw);
		const problem = datasetNameProblem(
			key,
			rows.filter((other) => other !== row).map((other) => other.key)
		);
		row.keyDraft = key;
		row.keyProblem = problem;
		// The stored value keeps the last valid name until this one is.
		if (problem) return;
		row.key = key;
		emit();
	}

	function setDefinition(row: Row, definition: string) {
		row.definition = definition;
		// A fresh input reads as the metric's own name, when still the default.
		const picked = definitions.find((option) => option.id === definition);
		if (picked && /^input(_\d+)?$/.test(row.key)) {
			const base = sanitizeDatasetName(picked.name.toLowerCase()).replace(/^(\d)/, '_$1');
			const key = uniqueKey(base || 'input');
			if (!datasetNameProblem(key, [])) row.key = key;
		}
		emit();
	}

	function setCombine(row: Row, combine: string) {
		row.combine = combine as Combine;
		emit();
	}

	const COMBINE_LABELS: Record<Combine, () => string> = {
		one: () => m.combineOne(),
		sum: () => m.combineSum(),
		avg: () => m.combineAvg(),
		min: () => m.combineMin(),
		max: () => m.combineMax(),
		count: () => m.combineCount()
	};
	const KEY_PROBLEM_MESSAGES = {
		required: () => m.inputKeyRequired(),
		invalid: () => m.datasetNameInvalid(),
		taken: () => m.inputKeyTaken()
	};
</script>

<div class="flex flex-col gap-2">
	{#each rows as row, index (index)}
		<div
			class="rounded-base border border-surface-200-800 bg-surface-50-950 p-3 flex flex-wrap items-start gap-2"
			data-testid="metric-input"
		>
			<label class="flex flex-col gap-1 w-36 shrink-0">
				<span class="text-xs font-semibold">{m.inputKey()}</span>
				<input
					type="text"
					class="input text-sm font-mono"
					value={row.keyDraft ?? row.key}
					oninput={(e) => setKey(row, e.currentTarget.value)}
					aria-invalid={row.keyProblem ? 'true' : undefined}
					data-testid="metric-input-key"
				/>
				{#if row.keyProblem}
					<span class="text-xs text-error-500">{KEY_PROBLEM_MESSAGES[row.keyProblem]()}</span>
				{/if}
			</label>
			<label class="flex flex-col gap-1 flex-1 min-w-48">
				<span class="text-xs font-semibold">{m.inputMetric()}</span>
				<select
					class="select text-sm w-full"
					value={row.definition}
					onchange={(e) => setDefinition(row, e.currentTarget.value)}
					data-testid="metric-input-definition"
				>
					<option value="" disabled>{m.selectAMetric()}</option>
					{#each definitions as option (option.id)}
						<option value={option.id}>{option.name}</option>
					{/each}
					{#if row.definition && !definitions.some((option) => option.id === row.definition)}
						<!-- A library URN, or a definition not offered here: kept as is. -->
						<option value={row.definition}>{row.definition}</option>
					{/if}
				</select>
			</label>
			<label class="flex flex-col gap-1 w-44 shrink-0">
				<span class="text-xs font-semibold">{m.inputCombine()}</span>
				<select
					class="select text-sm w-full"
					value={row.combine ?? 'one'}
					onchange={(e) => setCombine(row, e.currentTarget.value)}
					data-testid="metric-input-combine"
				>
					{#each COMBINES as combine (combine)}
						<option value={combine}>{COMBINE_LABELS[combine]()}</option>
					{/each}
				</select>
			</label>
			<button
				type="button"
				class="btn-icon preset-tonal mt-5 hover:preset-filled-error-500"
				title={m.delete()}
				aria-label={m.delete()}
				onclick={() => removeInput(index)}
			>
				<i class="fa-solid fa-trash"></i>
			</button>
		</div>
	{/each}
	<button
		type="button"
		class="btn preset-tonal text-xs self-start"
		onclick={addInput}
		data-testid="add-metric-input"
	>
		<i class="fa-solid fa-plus mr-1"></i>{m.addInput()}
	</button>
</div>
