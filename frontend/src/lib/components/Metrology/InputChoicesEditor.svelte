<script lang="ts">
	// For an instance of a metric computed from other metrics: what each input
	// finds in the instance's domain, and, when it finds several instances,
	// which one a "one value" input reads or which ones a combined input
	// leaves out. Deprecated instances are never offered: they are never read.
	import { m } from '$paraglide/messages';
	import {
		excludedOf,
		pickedOf,
		pickInstance,
		setIncluded,
		type InputChoices
	} from '$lib/utils/derived-metrics';

	interface Candidate {
		id: string;
		name: string;
		folder: string;
		status: string;
	}
	interface InputCandidates {
		key: string;
		combine: string;
		definition: { id: string; name: string } | null;
		candidates: Candidate[];
	}

	interface Props {
		// The form field as stored.
		value: unknown;
		definition: string | null | undefined;
		folder: string | null | undefined;
	}
	let { value = $bindable(), definition, folder }: Props = $props();

	let inputs = $state<InputCandidates[]>([]);
	let loaded = $state('');

	$effect(() => {
		const query = definition && folder ? `${definition}:${folder}` : '';
		if (query === loaded) return;
		loaded = query;
		if (!query) {
			inputs = [];
			return;
		}
		const params = new URLSearchParams({ definition: definition!, folder: folder! });
		fetch(`/fe-api/metrology/input-candidates?${params}`)
			.then((res) => (res.ok ? res.json() : { inputs: [] }))
			.then((body) => {
				if (loaded === query) inputs = body.inputs ?? [];
			})
			.catch(() => (inputs = []));
	});

	const choices = $derived((value ?? null) as InputChoices | null);
	const COMBINE_LABELS: Record<string, () => string> = {
		sum: () => m.combineSum(),
		avg: () => m.combineAvg(),
		min: () => m.combineMin(),
		max: () => m.combineMax(),
		count: () => m.combineCount()
	};
</script>

{#if inputs.length}
	<div
		class="form-group rounded-base border border-surface-200-800 p-3 flex flex-col gap-3"
		data-testid="input-choices"
	>
		<div class="flex flex-col gap-0.5">
			<span class="text-sm font-semibold">{m.inputChoices()}</span>
			<span class="text-xs text-surface-500">{m.inputChoicesHelpText()}</span>
		</div>
		{#each inputs as input (input.key)}
			<div class="flex flex-col gap-1" data-testid="input-choice">
				<div class="text-xs">
					<span class="font-mono font-semibold">{input.key}</span>
					<span class="text-surface-500">· {input.definition?.name ?? '?'}</span>
					{#if input.combine !== 'one'}
						<span class="badge preset-tonal-surface text-[10px] ml-1"
							>{COMBINE_LABELS[input.combine]?.() ?? input.combine}</span
						>
					{/if}
				</div>
				{#if input.candidates.length === 0}
					<p class="text-xs text-warning-600-400">{m.noInstanceForInput()}</p>
				{:else if input.combine === 'one' && input.candidates.length === 1}
					<p class="text-xs text-surface-500">
						{m.readsInstance()}
						{input.candidates[0].name} ({input.candidates[0].folder})
					</p>
				{:else if input.combine === 'one'}
					{@const picked = pickedOf(choices, input.key)}
					{#if !picked}
						<p class="text-xs text-warning-600-400">{m.pickInstanceToRead()}</p>
					{/if}
					{#each input.candidates as candidate (candidate.id)}
						<label class="flex items-center gap-2 text-sm cursor-pointer">
							<input
								type="radio"
								class="radio"
								name={`pick-${input.key}`}
								checked={picked === candidate.id}
								onchange={() => (value = pickInstance(choices, input.key, candidate.id))}
							/>
							{candidate.name}
							<span class="text-xs text-surface-500">{candidate.folder}</span>
						</label>
					{/each}
				{:else}
					{@const excluded = excludedOf(choices, input.key)}
					{#each input.candidates as candidate (candidate.id)}
						<label class="flex items-center gap-2 text-sm cursor-pointer">
							<input
								type="checkbox"
								class="checkbox"
								checked={!excluded.includes(candidate.id)}
								onchange={(e) =>
									(value = setIncluded(choices, input.key, candidate.id, e.currentTarget.checked))}
							/>
							{candidate.name}
							<span class="text-xs text-surface-500">{candidate.folder}</span>
						</label>
					{/each}
				{/if}
			</div>
		{/each}
	</div>
{/if}
