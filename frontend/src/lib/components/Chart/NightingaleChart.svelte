<script lang="ts">
	import { onMount } from 'svelte';
	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name = '';

	interface ndChartData {
		name: string;
		value: number;
	}
	export let values: ndChartData[]; // Set the types for these variables later on

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data
		var option = {
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
					itemStyle: {
						borderRadius: 5
					},
					data: values
				}
			]
		}; // console.debug(option);

		// use configuration item and data specified to show chart
		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}" />
