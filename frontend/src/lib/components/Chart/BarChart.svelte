<script lang="ts">
	import { onMount } from 'svelte';

	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';

	interface Props {
		name: string;
		values: any[]; // Set this type later
		labels: string[];
		horizontal?: boolean;
		title?: string;
		width?: string;
		height?: string;
		classesContainer?: string;
	}

	let {
		name,
		values,
		labels,
		horizontal = false,
		title = '',
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
			dispose = mountThemeAwareChart(echarts, el, () => {
				const category = {
					type: 'category',
					data: labels,
					axisTick: {
						alignWithLabel: true
					},
					axisLabel: {
						interval: 0
					},
					position: 'right'
				};

				const value = {
					type: 'value',
					allowDecimals: false,
					minInterval: 1
				};

				// specify chart configuration item and data
				let option = {
					toolbox: {
						show: true,
						feature: {
							mark: { show: true },
							dataView: { show: false, readOnly: true },
							saveAsImage: { show: false }
						}
					},
					tooltip: {},
					title: {
						text: title,
						textStyle: {
							fontWeight: 'bold',
							fontSize: 14
						}
						// show: false
					},
					grid: { left: 10, top: 40, right: 10, bottom: 10, containLabel: true },
					xAxis: horizontal ? value : category,
					yAxis: horizontal ? category : value,
					series: [
						{
							data: values,
							type: 'bar',
							itemStyle: {
								color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
									{ offset: 0, color: '#4f46e5' },
									{ offset: 1, color: '#7c3aed' }
								])
							}
						}
					]
				};

				// use configuration item and data specified to show chart
				return option;
			});
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
