<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		classesContainer?: string;
		name: string;
		value?: number;
	}

	let { classesContainer = '', name, value = 0 }: Props = $props();
	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data

		const gaugeData = [
			{
				value: value,
				detail: {
					valueAnimation: true,
					offsetCenter: ['0%', '0%']
				}
			}
		];
		var option = {
			series: [
				{
					type: 'gauge',
					radius: '120%',
					center: ['50%', '70%'],
					startAngle: 180,
					endAngle: 360,
					pointer: {
						show: false
					},
					progress: {
						show: true,
						overlap: false,
						roundCap: true,
						clip: false,
						itemStyle: {
							borderWidth: 1,
							borderColor: '#464646'
						}
					},
					axisLine: {
						lineStyle: {
							width: 20
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
					data: gaugeData,
					detail: {
						width: 40,
						height: 14,
						fontSize: 16,
						color: 'inherit',
						borderColor: 'inherit',
						borderRadius: 20,
						borderWidth: 1,
						formatter: '{value}%'
					}
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

<div id={chart_id} class=" {classesContainer} " style="width: 300px; height: 200px;"></div>
