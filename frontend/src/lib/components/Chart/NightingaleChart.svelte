<script lang="ts">
	import { onMount } from 'svelte';
	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';

	interface ndChartData {
		name: string;
		value: number;
	}
	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		// export let title = '';
		name?: string;
		values: ndChartData[]; // Set the types for these variables later on
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = '',
		values
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
				// Color mapping for CSF functions
				const colorMap: Record<string, string> = {
					'(undefined)': '#505372',
					Govern: '#FAE482',
					Identify: '#85C4EA',
					Protect: '#B29BBA',
					Detect: '#FAB647',
					Respond: '#E47677',
					Recover: '#8ACB93'
				};

				// Map data with specific colors
				const dataWithColors = values.map((item) => ({
					...item,
					itemStyle: {
						color: colorMap[item.name] || '#505372',
						borderRadius: 5
					}
				}));

				return {
					tooltip: {
						trigger: 'item',
						formatter: '{a} <br/>{b} : {c} ({d}%)'
					},
					series: [
						{
							name: 'Control Function',
							type: 'pie',
							radius: [20, 100],
							roseType: 'area',
							data: dataWithColors
						}
					]
				};
			});
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
