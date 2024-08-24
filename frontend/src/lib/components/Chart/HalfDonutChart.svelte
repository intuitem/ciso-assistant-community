<script lang="ts">
	import { onMount } from 'svelte';

	// export let name: string;
	export let s_label = '';

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name: string;

	interface riskChartData {
		name: string;
		value: number;
		color: string;
	}

	export let values: riskChartData[]; // Set the types for these variables later on
	export let colors: string[] = [];

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data
		var option = {
			title: {
				subtext: title
			},
			tooltip: {
				trigger: 'item'
			},
			series: [
				{
					name: 'risk level',
					type: 'pie',
					radius: ['40%', '70%'],
					center: ['50%', '70%'],
					// adjust the start and end angle
					startAngle: 180,
					endAngle: 360,
					data: values,
					color: colors
				}
			]
		};

		// console.debug(option);

		// use configuration item and data specified to show chart
		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}" />
