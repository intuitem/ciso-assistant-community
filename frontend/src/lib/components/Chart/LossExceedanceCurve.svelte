<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
		data?: Array<[number, number]>;
		title?: string;
		xAxisLabel?: string;
		yAxisLabel?: string;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = 'loss-exceedance',
		data = [
			[1000000, 0.1],
			[5000000, 0.05],
			[10000000, 0.02],
			[25000000, 0.01],
			[50000000, 0.005],
			[100000000, 0.002],
			[250000000, 0.001]
		],
		title = 'Loss Exceedance Curve',
		xAxisLabel = 'Loss Amount ($)',
		yAxisLabel = 'Exceedance Probability'
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
			grid: {
				show: false,
				left: '10%',
				right: '10%',
				top: '15%',
				bottom: '15%'
			},
			tooltip: {
				trigger: 'axis',
				formatter: function (params: any) {
					const point = params[0];
					return `${xAxisLabel}: $${point.value[0].toLocaleString()}<br/>${yAxisLabel}: ${(point.value[1] * 100).toFixed(2)}%`;
				}
			},
			xAxis: {
				type: 'log',
				name: xAxisLabel,
				nameLocation: 'middle',
				nameGap: 30,
				axisLabel: {
					formatter: function (value: number) {
						if (value >= 1000000000) {
							return '$' + (value / 1000000000).toFixed(0) + 'B';
						} else if (value >= 1000000) {
							return '$' + (value / 1000000).toFixed(0) + 'M';
						} else if (value >= 1000) {
							return '$' + (value / 1000).toFixed(0) + 'K';
						} else {
							return '$' + value.toFixed(0);
						}
					}
				},
				splitLine: {
					show: true,
					lineStyle: {
						color: '#e0e0e0',
						type: 'dashed'
					}
				}
			},
			yAxis: {
				type: 'value',
				name: yAxisLabel,
				nameLocation: 'middle',
				nameGap: 50,
				min: 0,
				max: 1,
				axisLabel: {
					formatter: function (value: number) {
						return (value * 100).toFixed(0) + '%';
					}
				},
				splitLine: {
					show: true,
					lineStyle: {
						color: '#e0e0e0',
						type: 'dashed'
					}
				}
			},
			series: [
				{
					name: 'Loss Exceedance',
					type: 'line',
					smooth: true,
					symbol: 'circle',
					symbolSize: 6,
					lineStyle: {
						color: '#ff6b6b',
						width: 3
					},
					itemStyle: {
						color: '#ff6b6b'
					},
					areaStyle: {
						opacity: 0.1,
						color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
							{
								offset: 0,
								color: '#ff6b6b'
							},
							{
								offset: 1,
								color: 'rgba(255, 107, 107, 0.05)'
							}
						])
					},
					data: data
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

<div
	id={chart_id}
	class="{height} {width} {classesContainer}"
	style="width: 600px; height: 400px;"
></div>
