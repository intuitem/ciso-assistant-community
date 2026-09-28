<script lang="ts">
	// Audit score scale: the framework's, the organisation's, a preset, or (for
	// copies) the baseline audit's. Options come from scaleOptions().
	import * as m from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { previewLevels, type ScaleOption } from '$lib/utils/score-scales';

	interface Props {
		options: ScaleOption[];
		selected: string;
		onSelect: (option: ScaleOption) => void;
		isScaleBound?: boolean;
		scoringEnabled?: boolean;
		// The existing audit's range, to announce a conversion when it changes.
		currentRange?: { min: number; max: number } | null;
	}

	let {
		options,
		selected,
		onSelect,
		isScaleBound = false,
		scoringEnabled = true,
		currentRange = null
	}: Props = $props();

	let selectedOption = $derived(options.find((o) => o.id === selected));
	let preview = $derived(selectedOption ? previewLevels(selectedOption, getLocale()) : []);
	let rangeChanges = $derived(
		Boolean(
			currentRange &&
			selectedOption &&
			(selectedOption.min !== currentRange.min || selectedOption.max !== currentRange.max)
		)
	);

	function title(option: ScaleOption): string {
		switch (option.source) {
			case 'framework':
				return m.scoreScaleFramework();
			case 'organisation':
				return m.scoreScaleOrganisation();
			case 'baseline':
				return m.scoreScaleBaseline();
			case 'current':
				return m.scoreScaleCurrent();
			default:
				return `${option.min}–${option.max}`;
		}
	}

	function subtitle(option: ScaleOption): string {
		if (option.source === 'preset') return option.preset?.label() ?? '';
		const range = `${option.min}–${option.max}`;
		return option.preset ? `${range} · ${option.preset.label()}` : range;
	}

	const chipClass = (active: boolean) =>
		`flex flex-col items-start rounded-md border px-3 py-1.5 text-left transition-colors ${
			active
				? 'border-primary-500 bg-primary-50-950 shadow-sm'
				: 'border-surface-200-800 hover:border-surface-400-600'
		}`;
</script>

<div class="space-y-3" data-testid="score-scale-picker">
	<div>
		<h3 class="font-semibold text-sm">{m.scoreScale()}</h3>
		<p class="text-xs text-surface-600-400">{m.scoreScaleHelpText()}</p>
	</div>

	{#if !scoringEnabled}
		<p class="flex gap-2 text-xs text-surface-500 italic" data-testid="score-scale-scoring-hidden">
			<i class="fa-solid fa-eye-slash mt-0.5"></i>
			<span>{m.scoreScaleScoringHidden({ section: m.fieldVisibility() })}</span>
		</p>
	{:else}
		{#if isScaleBound}
			<div
				class="flex gap-2 rounded-md border border-warning-500 bg-warning-50-950 px-3 py-2 text-xs"
				role="note"
			>
				<i class="fa-solid fa-lock mt-0.5"></i>
				<span>{m.scoreScaleBoundToFramework()}</span>
			</div>
		{/if}

		<div class="flex flex-wrap gap-2" role="radiogroup" aria-label={m.scoreScale()}>
			{#each options as option (option.id)}
				<button
					type="button"
					role="radio"
					aria-checked={option.id === selected}
					class={chipClass(option.id === selected)}
					data-testid={`score-scale-${option.id}`}
					onclick={() => option.id !== selected && onSelect(option)}
				>
					<span class="text-sm font-medium" class:font-mono={option.source === 'preset'}
						>{title(option)}</span
					>
					<span
						class="text-xs text-surface-600-400"
						class:font-mono={option.source !== 'preset' && !option.preset}>{subtitle(option)}</span
					>
				</button>
			{/each}
		</div>

		<p class="text-xs text-surface-600-400" data-testid="score-scale-preview">
			{#if preview.length}
				<span class="font-medium">{m.scoreScaleLevels()}</span>
				{#each preview as level, idx}
					<span class="font-mono text-surface-500">{level.score}</span>
					{level.name}{idx < preview.length - 1 ? ' · ' : ''}
				{/each}
			{:else}
				<span class="italic">{m.scoreScaleNoLabels()}</span>
			{/if}
		</p>

		{#if rangeChanges && currentRange && selectedOption}
			<p class="flex gap-2 text-xs text-surface-600-400" data-testid="score-scale-conversion-note">
				<i class="fa-solid fa-arrow-right-arrow-left mt-0.5"></i>
				<span
					>{m.scoreScaleConversionNote({
						from: `${currentRange.min}–${currentRange.max}`,
						to: `${selectedOption.min}–${selectedOption.max}`
					})}</span
				>
			</p>
		{/if}
	{/if}
</div>
