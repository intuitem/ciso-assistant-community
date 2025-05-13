<script lang="ts">
	import { onMount } from 'svelte';
	

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

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
