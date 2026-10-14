<script lang="ts">
	// A formula's recent results as a small chart, and the metric as it is now
	// beside them when there is one: a dashed line on the same scale, so an
	// edit reads as the change it makes.
	import { m } from '$paraglide/messages';
	import { sparkline, sparkRange, type SparkPoint } from '$lib/utils/derived-metrics';

	type Period = { start: string; value: unknown; skipped?: boolean };
	interface Props {
		// Numbers to plot (a level as its position), oldest first.
		periods: Period[];
		// The same slots, as the metric holds them now.
		now?: Period[];
		width: number;
		height: number;
		format: (value: number) => string;
		testid?: string;
	}

	let { periods, now = [], width, height, format, testid = 'formula-chart' }: Props = $props();

	const chartId = $props.id();
	const range = $derived(sparkRange(periods, now));
	const chart = $derived(sparkline(periods, width, height, 6, range));
	const nowChart = $derived(sparkline(now, width, height, 6, range));
	const nowAt = $derived(new Map(now.map((period) => [period.start, period])));
	let hovered = $state<SparkPoint | null>(null);
</script>

{#if chart}
	<figure class="flex flex-col gap-1" data-testid={testid}>
		<svg
			viewBox="0 0 {width} {height}"
			class="w-full h-auto overflow-visible text-primary-500"
			role="img"
			aria-label={m.recentResults()}
			onmouseleave={() => (hovered = null)}
		>
			<defs>
				<linearGradient id="{chartId}-fill" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0%" stop-color="currentColor" stop-opacity="0.35" />
					<stop offset="100%" stop-color="currentColor" stop-opacity="0" />
				</linearGradient>
			</defs>
			{#if nowChart}
				<!-- The metric as it is now, under the line the edit would give. -->
				<path
					d={nowChart.line}
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-dasharray="4 3"
					stroke-linejoin="round"
					class="text-surface-500"
					data-testid="{testid}-now"
				/>
			{/if}
			<!-- Keyed on the shape: a new formula draws its line again. -->
			{#key chart.line}
				<path d={chart.area} fill="url(#{chartId}-fill)" class="spark-area" />
				<path
					d={chart.line}
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linejoin="round"
					stroke-linecap="round"
					pathLength="1"
					class="spark-line"
				/>
			{/key}
			{#each chart.points as point, index (point.start)}
				{@const latest = index === chart.points.length - 1}
				{#if latest}
					<circle cx={point.x} cy={point.y} r="3.5" fill="currentColor" class="spark-pulse" />
				{/if}
				<circle
					cx={point.x}
					cy={point.y}
					r={latest || hovered === point ? 3.5 : 2}
					fill="currentColor"
				/>
				<!-- A wider, invisible target than the dot itself. -->
				<circle
					cx={point.x}
					cy={point.y}
					r="9"
					fill="transparent"
					role="presentation"
					onmouseenter={() => (hovered = point)}
				/>
			{/each}
		</svg>
		<figcaption class="flex justify-between text-[10px] font-mono text-surface-500">
			{#if hovered}
				{@const held = nowAt.get(hovered.start)}
				<span>{hovered.start.slice(0, 10)}</span>
				<span class="flex gap-2">
					{#if held && !held.skipped && typeof held.value === 'number'}
						<span>{m.formulaNow()} {format(held.value)}</span>
					{/if}
					<span class="text-surface-900-100 font-semibold">{format(hovered.value)}</span>
				</span>
			{:else}
				<span>{chart.points[0].start.slice(0, 10)}</span>
				<span>{chart.points[chart.points.length - 1].start.slice(0, 10)}</span>
			{/if}
		</figcaption>
		{#if nowChart}
			<div
				class="flex items-center gap-4 text-[11px] text-surface-600-400"
				data-testid="{testid}-legend"
			>
				<span class="flex items-center gap-1.5">
					<svg width="18" height="4" aria-hidden="true" class="text-surface-500">
						<line
							x1="0"
							y1="2"
							x2="18"
							y2="2"
							stroke="currentColor"
							stroke-width="1.5"
							stroke-dasharray="4 3"
						/>
					</svg>{m.formulaNow()}
				</span>
				<span class="flex items-center gap-1.5">
					<svg width="18" height="4" aria-hidden="true" class="text-primary-500">
						<line x1="0" y1="2" x2="18" y2="2" stroke="currentColor" stroke-width="2" />
					</svg>{m.formulaNew()}
				</span>
			</div>
		{/if}
	</figure>
{/if}

<style>
	/* The line draws itself in, the area fades in under it, and the latest
	   point breathes: a formula's result arriving, not a static picture. */
	.spark-line {
		stroke-dasharray: 1;
		animation: spark-draw 0.8s ease-out;
	}
	.spark-area {
		animation: spark-fade 0.8s ease-out;
	}
	.spark-pulse {
		transform-box: fill-box;
		transform-origin: center;
		animation: spark-pulse 2s ease-out infinite;
	}
	@keyframes spark-draw {
		from {
			stroke-dashoffset: 1;
		}
	}
	@keyframes spark-fade {
		from {
			opacity: 0;
		}
	}
	@keyframes spark-pulse {
		from {
			opacity: 0.6;
			transform: scale(1);
		}
		to {
			opacity: 0;
			transform: scale(3);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.spark-line,
		.spark-area,
		.spark-pulse {
			animation: none;
		}
	}
</style>
