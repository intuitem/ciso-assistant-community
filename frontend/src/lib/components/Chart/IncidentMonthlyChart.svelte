<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
		title?: string;
		months?: string[];
		monthlyCount?: number[];
		cumulativeCount?: number[];
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = 'incident_monthly_chart',
		title = '',
		months = [],
		monthlyCount = [],
		cumulativeCount = []
	}: Props = $props();

	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const option = {
			title: {
				text: title,
				left: 'center',
				textStyle: {
					fontSize: 16,
					fontWeight: 'bold'
				}
			},
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'cross',
					crossStyle: {
						color: '#999'
					}
				}
			},
			legend: {
				data: [m.monthlyCount(), m.cumulativeCount()],
				bottom: 10
			},
			grid: {
				left: '10%',
				right: '10%',
				bottom: '15%',
				top: '15%',
				containLabel: true
			},
			xAxis: [
				{
					type: 'category',
					data: months,
					axisPointer: {
						type: 'shadow'
					}
				}
			],
			yAxis: [
				{
					type: 'value',
					name: m.monthlyCount(),
					position: 'left',
					axisLabel: {
						formatter: '{value}',
						color: '#0891B2'
					},
					axisLine: {
						show: true,
						lineStyle: {
							color: '#0891B2'
						}
					},
					splitLine: {
						show: true,
						lineStyle: {
							color: '#E5E7EB',
							type: 'solid'
						}
					},
					minInterval: 1,
					min: 0
				},
				{
					type: 'value',
					name: m.cumulativeCount(),
					position: 'right',
					axisLabel: {
						formatter: '{value}',
						color: '#D97706'
					},
					axisLine: {
						show: true,
						lineStyle: {
							color: '#D97706'
						}
					},
					splitLine: {
						show: false
					},
					minInterval: 1,
					min: 0
				}
			],
			series: [
				{
					name: m.monthlyCount(),
					type: 'bar',
					yAxisIndex: 0,
					data: monthlyCount,
					itemStyle: {
						color: {
							type: 'linear',
							x: 0,
							y: 0,
							x2: 0,
							y2: 1,
							colorStops: [
								{
									offset: 0,
									color: '#06B6D4' // cyan-500
								},
								{
									offset: 1,
									color: '#0891B2' // cyan-600
								}
							]
						}
					},
					emphasis: {
						itemStyle: {
							color: {
								type: 'linear',
								x: 0,
								y: 0,
								x2: 0,
								y2: 1,
								colorStops: [
									{
										offset: 0,
										color: '#0891B2' // cyan-600
									},
									{
										offset: 1,
										color: '#0E7490' // cyan-700
									}
								]
							}
						}
					}
				},
				{
					name: m.cumulativeCount(),
					type: 'line',
					yAxisIndex: 1,
					data: cumulativeCount,
					lineStyle: {
						color: '#D97706',
						width: 3,
						shadowColor: 'rgba(217, 119, 6, 0.3)',
						shadowBlur: 4,
						shadowOffsetY: 2
					},
					itemStyle: {
						color: '#D97706',
						borderColor: '#FFFFFF',
						borderWidth: 2,
						shadowColor: 'rgba(217, 119, 6, 0.4)',
						shadowBlur: 6
					},
					symbol: 'circle',
					symbolSize: 8,
					smooth: true
				}
			]
		};

		chart.setOption(option);

		const resizeHandler = function () {
			chart.resize();
		};

		window.addEventListener('resize', resizeHandler);

		// Cleanup function
		return () => {
			chart.dispose();
			window.removeEventListener('resize', resizeHandler);
		};
	});
</script>

<div
	id={chart_id}
	class="{height} {width} {classesContainer}"
	style="width: 100%; height: 100%;"
></div>
