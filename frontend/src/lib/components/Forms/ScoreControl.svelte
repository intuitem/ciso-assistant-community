<script lang="ts">
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import { Progress } from '@skeletonlabs/skeleton-svelte';

	interface ScoreDefinition {
		score: number;
		name: string;
		description?: string;
		description_doc?: string;
	}

	/**
	 * Fresh, controlled score widget (no superForm dependency).
	 * Compact enough to live in a row header: optional on/off toggle + slider + ring.
	 * Set `editable={false}` for a read-only ring (computed or locked scores).
	 */
	interface Props {
		value?: number | null;
		onChange?: (value: number) => void;
		min?: number;
		max?: number;
		step?: number;
		scoresDefinition?: ScoreDefinition[];
		editable?: boolean;
		/** When provided, renders an on/off toggle wired to `onScoredChange`. */
		scored?: boolean;
		onScoredChange?: (scored: boolean) => void;
		disabled?: boolean;
		label?: string;
		isDoc?: boolean;
	}
	let {
		value = null,
		onChange = () => {},
		min = 0,
		max = 100,
		step,
		scoresDefinition = [],
		editable = true,
		scored,
		onScoredChange,
		disabled = false,
		label,
		isDoc = false
	}: Props = $props();

	const resolvedStep = $derived(step ?? (max === 100 ? 5 : 1));
	const active = $derived(scored !== false);
	const sliderDisabled = $derived(disabled || !active);

	// Internal display value so the slider/ring react immediately to dragging,
	// even when the parent keeps the score on a non-reactive object.
	let internal = $state(value ?? min);
	$effect(() => {
		internal = value ?? min;
	});

	const definition = $derived((scoresDefinition ?? []).find((d) => d.score === internal));
	const definitionText = $derived(
		isDoc ? (definition?.description_doc ?? definition?.description) : definition?.description
	);
</script>

<div class="flex items-center gap-2">
	{#if label}
		<span class="text-xs font-semibold text-surface-500 whitespace-nowrap">{label}</span>
	{/if}

	{#if scored !== undefined && onScoredChange}
		<button
			type="button"
			role="switch"
			aria-checked={active}
			aria-label={label}
			{disabled}
			onclick={() => onScoredChange(!active)}
			class="relative h-5 w-9 shrink-0 rounded-full transition-colors {active
				? 'bg-primary-500'
				: 'bg-surface-300'} {disabled ? 'opacity-50' : ''}"
		>
			<span
				class="absolute top-0.5 size-4 rounded-full bg-white transition-all {active
					? 'left-[18px]'
					: 'left-0.5'}"
			></span>
		</button>
	{/if}

	{#if editable}
		<input
			data-testid="range-slider-input"
			type="range"
			class="input w-28 px-0 {sliderDisabled ? 'opacity-50' : ''}"
			bind:value={internal}
			{min}
			{max}
			step={resolvedStep}
			disabled={sliderDisabled}
			oninput={() => onChange(internal)}
		/>
	{/if}

	<div class="relative shrink-0" title={definition?.name}>
		<Progress value={formatScoreValue(internal, max, false, min)} min={0} max={100}>
			<Progress.Circle class="[--size:--spacing(9)]">
				<Progress.CircleTrack />
				<Progress.CircleRange class={displayScoreColor(internal, max, false, min)} />
			</Progress.Circle>
			<div class="absolute inset-0 flex items-center justify-center">
				<span class="text-xs font-bold">{active ? internal : '--'}</span>
			</div>
		</Progress>
	</div>

	{#if active && definition?.name}
		<span class="text-xs text-surface-500 truncate max-w-[12rem]" title={definitionText}
			>{definition.name}</span
		>
	{/if}
</div>
