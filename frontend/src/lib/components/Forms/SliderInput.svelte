<script lang="ts">
	import { Tooltip } from '@skeletonlabs/skeleton-svelte';
	import * as m from '$paraglide/messages';

	interface Choice {
		urn: string;
		value: string;
		description?: string | null;
	}

	interface Props {
		mode: 'number' | 'choice';
		value: number | string | null;
		disabled?: boolean;
		ariaLabel?: string;
		// number mode
		min?: number;
		max?: number;
		step?: number;
		// choice mode
		choices?: Choice[];
		onChange: (next: number | string | null) => void;
	}

	let {
		mode,
		value,
		disabled = false,
		ariaLabel = '',
		min = 0,
		max = 100,
		step = 1,
		choices = [],
		onChange
	}: Props = $props();

	// Choice mode: positions are 0..N where 0 = null, 1..N = choices[i-1] in order.
	const choiceCount = $derived(choices.length);

	// Resolve the current slider position (number) from the bound value.
	const sliderPosition = $derived.by(() => {
		if (mode === 'number') {
			if (value === null || typeof value !== 'number') return min;
			return Math.min(max, Math.max(min, value));
		}
		// choice mode
		if (value === null) return 0;
		const idx = choices.findIndex((c) => c.urn === value);
		// URN not found → orphan answer, sit at null sentinel
		return idx === -1 ? 0 : idx + 1;
	});

	// Label below the thumb. Number mode shows the em-dash sentinel whenever
	// the bound value is null (untouched or cleared) — deriving directly from
	// `value` keeps this in sync when the parent resets the answer externally.
	const activeLabel = $derived.by(() => {
		if (mode === 'number') {
			if (value === null) return '—';
			return String(sliderPosition);
		}
		// choice mode
		if (sliderPosition === 0) return '—';
		const c = choices[sliderPosition - 1];
		return c?.value ?? '—';
	});

	const activeDescription = $derived.by(() => {
		if (mode !== 'choice') return null;
		if (sliderPosition === 0) return null;
		return choices[sliderPosition - 1]?.description ?? null;
	});

	function handleInput(e: Event) {
		const raw = (e.currentTarget as HTMLInputElement).valueAsNumber;
		if (mode === 'number') {
			onChange(raw);
		} else {
			if (raw === 0) {
				onChange(null);
			} else {
				const c = choices[raw - 1];
				onChange(c?.urn ?? null);
			}
		}
	}

	function clear() {
		onChange(null);
	}

	const showThumb = $derived(mode === 'choice' || value !== null);
</script>

<div class="flex flex-col gap-1 w-full">
	<div class="flex items-center gap-2">
		<div class="flex-1 flex flex-col gap-0.5">
			<input
				type="range"
				class="input w-full px-0 {showThumb ? '' : 'opacity-40'}"
				min={mode === 'number' ? min : 0}
				max={mode === 'number' ? max : choiceCount}
				step={mode === 'number' ? step : 1}
				value={sliderPosition}
				{disabled}
				aria-label={ariaLabel}
				aria-valuenow={sliderPosition}
				aria-valuemin={mode === 'number' ? min : 0}
				aria-valuemax={mode === 'number' ? max : choiceCount}
				aria-valuetext={activeLabel}
				oninput={handleInput}
			/>
			{#if mode === 'choice' && choiceCount > 0}
				<div class="flex justify-between pointer-events-none px-1.5" aria-hidden="true">
					{#each Array(choiceCount + 1) as _, i (i)}
						<span class="w-px h-1.5 {i === sliderPosition ? 'bg-blue-500' : 'bg-gray-400'}"></span>
					{/each}
				</div>
			{/if}
		</div>
		{#if mode === 'number' && value !== null && !disabled}
			<button
				type="button"
				class="text-gray-400 hover:text-red-500 transition-colors"
				aria-label={m.clearAnswer()}
				onclick={clear}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		{/if}
	</div>

	<div class="flex items-center justify-center text-sm font-medium text-gray-700">
		<span>{activeLabel}</span>
		{#if activeDescription}
			<Tooltip positioning={{ placement: 'top' }} openDelay={50}>
				<Tooltip.Trigger>
					{#snippet child({ props })}
						<span {...props} class="ml-2 underline">
							<i class="fa-solid fa-circle-info"></i>
						</span>
					{/snippet}
				</Tooltip.Trigger>
				<Tooltip.Positioner>
					<Tooltip.Content class="card preset-filled p-4">{activeDescription}</Tooltip.Content>
				</Tooltip.Positioner>
			</Tooltip>
		{/if}
	</div>
</div>
