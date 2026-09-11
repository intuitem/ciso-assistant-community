<script lang="ts">
	import { onMount } from 'svelte';

	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';

	interface Series {
		name: string;
		data: number[];
	}

	interface Props {
		name: string;
		title?: string;
		categories: string[];
		series: Series[];
		/** Swap the axes so long category labels get the horizontal room. */
		horizontal?: boolean;
		/** Stack group name; omit to keep the bars side by side. */
		stack?: string;
		/** Series colors, in series order; omit for the theme palette. */
		colors?: string[];
		/** Called with the clicked category index; omit to leave the bars inert. */
		onSelect?: (index: number) => void;
		width?: string;
		height?: string;
		classesContainer?: string;
	}

	let {
		name,
		title = '',
		categories,
		series,
		horizontal = false,
		stack,
		colors,
		onSelect,
		width = 'w-auto',
		height = 'h-full',
		classesContainer = ''
	}: Props = $props();

	const chart_id = `${name}_div`;

	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			if (!active) return;
			const el = document.getElementById(chart_id);
			if (!el) return;
			dispose = mountThemeAwareChart(
				echarts,
				el,
				() => {
					const categoryAxis = {
						type: 'category',
						data: categories,
						axisTick: {
							alignWithLabel: true
						},
						axisLabel: {
							interval: 0,
							rotate: 0
						}
					};
					const valueAxis = {
						type: 'value',
						allowDecimals: false,
						minInterval: 1
					};
					const option = {
						title: {
							text: title,
							textStyle: {
								fontWeight: 'bold',
								fontSize: 14
							}
						},
						tooltip: {
							trigger: 'axis',
							axisPointer: {
								type: 'shadow'
							}
						},
						legend: {
							bottom: 0,
							left: 'center'
						},
						grid: {
							left: 0,
							top: 40,
							// containLabel keeps labels inside the grid, but the last value-axis
							// tick is centred on the edge, so half of it still overflows.
							right: horizontal ? 16 : 0,
							bottom: 40,
							containLabel: true
						},
						xAxis: horizontal ? valueAxis : categoryAxis,
						yAxis: horizontal ? categoryAxis : valueAxis,
						...(colors?.length ? { color: colors } : {}),
						series: series.map((s) => ({
							name: s.name,
							type: 'bar',
							data: s.data,
							stack,
							emphasis: {
								focus: 'series'
							}
						}))
					};

					return option;
				},
				// onChart re-fires when a theme flip re-inits the chart, so the handler
				// survives it; a listener attached once outside would be lost.
				onSelect
					? {
							onChart: (chart: any) =>
								chart.on('click', (params: any) => {
									if (params.dataIndex !== undefined) onSelect(params.dataIndex);
								})
						}
					: undefined
			);
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
