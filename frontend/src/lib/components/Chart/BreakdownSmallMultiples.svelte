<script lang="ts">
	import { onMount } from 'svelte';
	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';
	import { m } from '$paraglide/messages';

	interface Panel {
		key: string;
		label: string;
		color: string;
		values: number[];
	}

	interface Props {
		panels?: Panel[];
		categories?: string[];
	}

	let { panels = [], categories = [] }: Props = $props();

	let holders: HTMLElement[] = $state([]);
	let echartsModule = $state<any>(null);

	const summaries = $derived(
		panels.map((panel) => {
			const values = panel.values;
			const last = values.length ? values[values.length - 1] : 0;
			const delta = values.length ? last - values[0] : 0;
			return { last, delta };
		})
	);

	// A breakdown key can be user-supplied text — qualification names reach the
	// breakdown as keys — and an ECharts formatter that returns a string has it
	// rendered as HTML.
	const HTML_ESCAPES: Record<string, string> = {
		'&': '&amp;',
		'<': '&lt;',
		'>': '&gt;',
		'"': '&quot;',
		"'": '&#39;'
	};

	function escapeHtml(value: unknown): string {
		return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
	}

	onMount(() => {
		let active = true;
		import('echarts').then((module) => {
			if (active) echartsModule = module;
		});
		return () => {
			active = false;
		};
	});

	// The parent keys this component on sample-array length, but a day's snapshot
	// is updated in place, so the same length can carry different values — and a
	// newly appearing status adds a panel without changing that length either.
	// Rebuilding on every input change is what keeps the panels truthful.
	$effect(() => {
		const echarts = echartsModule;
		const currentPanels = panels;
		const currentCategories = categories;
		if (!echarts || currentPanels.length === 0) return;

		const disposers: Array<() => void> = [];
		currentPanels.forEach((panel, index) => {
			const element = holders[index];
			if (!element) return;
			const values = panel.values;
			const last = values.length ? values[values.length - 1] : 0;

			disposers.push(
				mountThemeAwareChart(echarts, element, () => ({
					grid: { left: 2, right: 2, top: 6, bottom: 2 },
					tooltip: {
						trigger: 'axis',
						confine: true,
						formatter: (params: any) =>
							`${escapeHtml(params[0].axisValue)}<br/>${params[0].marker}` +
							`${escapeHtml(panel.label)}: <b>${escapeHtml(params[0].value)}</b>`
					},
					xAxis: {
						type: 'category',
						data: currentCategories,
						show: false,
						boundaryGap: false
					},
					// Each panel is padded to its own range, so a flat series reads as flat
					// instead of as noise amplified to fill the box.
					yAxis: {
						type: 'value',
						show: false,
						min: (v: any) => Math.max(0, v.min - Math.max(1, (v.max - v.min) * 0.5)),
						max: (v: any) => v.max + Math.max(1, (v.max - v.min) * 0.5)
					},
					series: [
						{
							name: panel.label,
							type: 'line',
							smooth: true,
							showSymbol: false,
							lineStyle: { width: 2, color: panel.color },
							areaStyle: { opacity: 0.16, color: panel.color },
							markPoint: {
								symbol: 'circle',
								symbolSize: 7,
								label: { show: false },
								itemStyle: { color: panel.color },
								data: [{ coord: [currentCategories.length - 1, last] }]
							},
							data: values
						}
					]
				}))
			);
		});

		return () => disposers.forEach((dispose) => dispose());
	});
</script>

{#if panels.length === 0}
	<div class="flex items-center justify-center h-full text-surface-400-600 text-sm">
		{m.noDataAvailable()}
	</div>
{:else}
	<div
		class="grid gap-px bg-surface-200-800 h-full overflow-auto"
		style="grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));"
	>
		{#each panels as panel, index (panel.key)}
			{@const summary = summaries[index]}
			<div class="bg-surface-50-950 p-3 flex flex-col gap-0.5 min-w-0">
				<span class="flex items-center gap-1.5 text-xs text-surface-600-400 truncate">
					<span
						class="w-2 h-2 rounded-xs shrink-0"
						style="background-color: {panel.color}"
						aria-hidden="true"
					></span>
					<span class="truncate">{panel.label}</span>
				</span>
				<span class="text-xl font-semibold tabular-nums text-surface-900-100">
					{summary.last}
					{#if summary.delta !== 0}
						<span class="text-xs font-medium text-surface-500-500">
							{summary.delta > 0 ? '+' : ''}{summary.delta}
						</span>
					{/if}
				</span>
				<div class="h-10" bind:this={holders[index]}></div>
			</div>
		{/each}
	</div>
{/if}
