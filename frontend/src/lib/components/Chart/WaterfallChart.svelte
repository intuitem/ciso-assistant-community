<script lang="ts">
	import { onMount } from 'svelte';

	
	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		// export let title = '';
		name?: string;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = ''
	}: Props = $props();

	// interface waterfallData {
	// 	placeholder: number[];
	// 	progress: number[];
	// }

	// export let values: waterfallData; // Set the types for these variables later on

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data
		var option = {
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow'
				},
				formatter: function (params) {
					var tar = params[1];
					return tar.name + '<br/>' + tar.seriesName + ' : ' + tar.value;
				}
			},
			grid: {
				left: '3%',
				right: '4%',
				bottom: '3%',
				containLabel: true
			},
			xAxis: {
				type: 'category',
				splitLine: { show: false },
				data: ['Total', 'To do', 'In progress', 'On hold', 'Done', 'Expired']
			},
			yAxis: {
				type: 'value',
				show: false
			},
			series: [
				{
					name: 'Placeholder',
					type: 'bar',
					stack: 'Total',
					itemStyle: {
						borderColor: 'transparent',
						color: 'transparent'
					},
					emphasis: {
						itemStyle: {
							borderColor: 'transparent',
							color: 'transparent'
						}
					},
					data: [0, 170, 140, 120, 30, 0]
				},
				{
					name: 'Progress',
					type: 'bar',
					stack: 'Total',
					label: {
						show: true,
						position: 'inside'
					},
					data: [290, 120, 30, 0, 90, 0]
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

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
