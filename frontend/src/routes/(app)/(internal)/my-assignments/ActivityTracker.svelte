<script lang="ts">
	import { onMount } from 'svelte';
	export let classesContainer = '';
	export let name = 'act_tracker';
	export let metrics;
	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data

		const gaugeData = [
			{
				value: metrics.progress.audits,
				name: 'audits',
				title: {
					offsetCenter: ['0%', '-20%']
				},
				detail: {
					valueAnimation: true,
					offsetCenter: ['0%', '-30%']
				}
			},
			{
				value: metrics.progress.controls,
				name: 'controls',
				title: {
					offsetCenter: ['0%', '10%']
				},
				detail: {
					valueAnimation: true,
					offsetCenter: ['0%', '0%']
				}
			},
			{
				value: metrics.progress.evidences,
				name: 'evidences',
				title: {
					offsetCenter: ['0%', '40%']
				},
				detail: {
					valueAnimation: true,
					offsetCenter: ['0%', '30%']
				}
			}
		];
		var option = {
			color: ['#B075CC', '#91CC75', '#75BDCC'],
			series: [
				{
					type: 'gauge',
					radius: '100%',
					center: ['50%', '50%'],
					startAngle: 90,
					endAngle: -270,
					pointer: {
						show: false
					},
					tooltip: {
						show: true
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
							width: 66
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
						fontSize: 14,
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

<div id={chart_id} class=" {classesContainer} " style="width: 400px; height: 400px;" />
