<script lang="ts">
	import { onMount } from 'svelte';

	export let classesContainer = '';
	export let name = 'single_gauge';
	export let value: number;
	export let max: number;
	export let isPercentage = false;

	const chart_id = `${name}_div`;

	// Calculate percentage
	$: percentage = Math.round((value / max) * 100);

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const option = {
			series: [
				{
					type: 'gauge',
					radius: '90%',
					center: ['50%', '50%'],
					startAngle: 90,
					endAngle: -270,
					min: 0,
					max: 100,
					pointer: {
						show: false
					},
					progress: {
						show: true,
						width: 30,
						roundCap: true,
						itemStyle: {
							color: '#B075CC'
						}
					},
					axisLine: {
						lineStyle: {
							width: 30,
							color: [[1, '#E6E6E6']]
						}
					},
					splitLine: {
						show: false
					},
					axisTick: {
						show: false
					},
					axisLabel: {
						show: false
					},
					data: [
						{
							value: percentage,
							detail: {
								valueAnimation: true,
								offsetCenter: ['0%', '0%'],
								fontSize: 48,
								fontWeight: 'bold',
								color: '#333',
								formatter: function (value) {
									const displayValue = Math.round((value / 100) * max);
									return isPercentage ? `${displayValue}%` : displayValue;
								}
							}
						}
					],
					detail: {
						width: 80,
						height: 60,
						fontSize: 48,
						fontWeight: 'bold',
						color: '#333',
						backgroundColor: 'transparent',
						borderWidth: 0
					}
				}
			]
		};

		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});

		return () => {
			chart.dispose();
		};
	});
</script>

<div id={chart_id} class={classesContainer} style="width: 400px; height: 400px;" />
