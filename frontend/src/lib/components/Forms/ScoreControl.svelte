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
	 * Controlled score widget: slider + ring.
	 * `editable={false}` renders a read-only ring.
	 */
	interface Props {
		value?: number | null;
		onChange?: (value: number) => void;
		min?: number;
		max?: number;
		step?: number;
		scoresDefinition?: ScoreDefinition[];
		editable?: boolean;
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
		disabled = false,
		label,
		isDoc = false
	}: Props = $props();

	const resolvedStep = $derived(step ?? (max === 100 ? 5 : 1));

	// Internal value; slider/ring react during drag
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

	{#if editable}
		<input
			data-testid="range-slider-input"
			type="range"
			class="input w-28 px-0 {disabled ? 'opacity-50' : ''}"
			bind:value={internal}
			{min}
			{max}
			step={resolvedStep}
			{disabled}
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
				<span class="text-xs font-bold">{value != null ? internal : '--'}</span>
			</div>
		</Progress>
	</div>

	{#if definition?.name}
		<span class="text-xs text-surface-500 truncate max-w-[12rem]" title={definitionText}
			>{definition.name}</span
		>
	{/if}
</div>
