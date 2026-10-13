<script lang="ts">
	import { getLocale } from '$paraglide/runtime';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { m } from '$paraglide/messages';
	import { addDays, type Milestone } from './trajectory';

	interface Props {
		today: string;
		totalDays: number;
		dayOffset: number;
		milestones: Milestone[];
		hovered?: Milestone | null;
		labelOf: (scenarioId: string) => string;
		onscrub?: () => void;
	}

	let {
		today,
		totalDays,
		dayOffset = $bindable(),
		milestones,
		hovered = $bindable(null),
		labelOf,
		onscrub
	}: Props = $props();

	const format = (iso: string) => formatDateOrDateTime(iso, getLocale()) ?? iso;

	let currentDate = $derived(addDays(today, Math.round(dayOffset)));
	let pct = (offset: number) => (totalDays > 0 ? (offset / totalDays) * 100 : 0);
</script>

<div class="flex flex-col gap-1" data-testid="trajectory-timeline">
	<div class="flex items-baseline gap-2">
		<span class="text-lg font-semibold tabular-nums">{format(currentDate)}</span>
		{#if dayOffset === 0}
			<span class="text-xs text-surface-600-400">{m.today()}</span>
		{/if}
	</div>
	<div class="relative pt-1 pb-4">
		<input
			type="range"
			min="0"
			max={totalDays}
			step="1"
			bind:value={dayOffset}
			oninput={() => onscrub?.()}
			class="w-full accent-primary-500"
			data-testid="trajectory-scrubber"
		/>
		<div class="absolute inset-x-2 bottom-0 h-4">
			{#each milestones as milestone (milestone.date)}
				<button
					type="button"
					class="absolute -translate-x-1/2 top-0 w-2.5 h-2.5 rounded-full border-2 border-primary-500 transition-transform hover:scale-150 {milestone.offset <=
					dayOffset
						? 'bg-primary-500'
						: 'bg-surface-50-950'}"
					style="left: {pct(milestone.offset)}%;"
					aria-label={format(milestone.date)}
					onmouseenter={() => (hovered = milestone)}
					onmouseleave={() => (hovered = null)}
					onfocus={() => (hovered = milestone)}
					onblur={() => (hovered = null)}
					onclick={() => {
						dayOffset = milestone.offset;
						onscrub?.();
					}}
				></button>
			{/each}
		</div>
	</div>
	<div class="flex justify-between text-xs text-surface-600-400">
		<span>{format(today)}</span>
		<span>{format(addDays(today, totalDays))}</span>
	</div>
	<div class="min-h-5 text-sm">
		{#if hovered}
			<span class="font-semibold">{format(hovered.date)}</span>
			·
			{hovered.controls.map((c) => c.name).join(', ')}
			<i class="fa-solid fa-arrow-right mx-1 text-xs"></i>
			{hovered.scenarioIds.map(labelOf).join(', ')}
		{/if}
	</div>
</div>
