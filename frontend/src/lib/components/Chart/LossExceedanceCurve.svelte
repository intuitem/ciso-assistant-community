<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
		data?: Array<[number, number]>;
		toleranceData?: Array<[number, number]>;
		title?: string;
		xAxisLabel?: string;
		yAxisLabel?: string;
		minorSplitLine?: boolean;
		enableTooltip?: boolean;
		xAxisScale?: 'linear' | 'log';
		yAxisScale?: 'linear' | 'log';
		showXGrid?: boolean;
		showYGrid?: boolean;
		xMax?: number;
		xMin?: number;
		autoYMax?: boolean;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = 'loss-exceedance',
		data = undefined,
		toleranceData = undefined,
		title = 'Loss Exceedance Curve',
		xAxisLabel = 'Loss Amount ($)',
		yAxisLabel = 'Exceedance Probability',
		minorSplitLine = false,
		enableTooltip = false,
		showXGrid = true,
		showYGrid = true,
		xMax = 1000000,
		xMin = undefined,
		autoYMax = false,
		xAxisScale = 'log',
		yAxisScale = 'linear',
	}: Props = $props();

	const chart_id = `${name}_div`;

	// Use provided xMin or calculate from data, fallback to xMax/100000
	const calculatedXMin = xMin ?? (xMax ? xMax / 100000 : undefined);

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
				show: !!enableTooltip,
				trigger: 'axis',
				formatter: function (params: any) {
					const point = params[0];
					return `${xAxisLabel}: $${point.value[0].toLocaleString()}<br/>${yAxisLabel}: ${(point.value[1] * 100).toFixed(2)}%`;
				}
			},
			xAxis: {
				type: xAxisScale,
				name: xAxisLabel,
				nameLocation: 'middle',
				min: calculatedXMin,
				max: xMax,
				nameGap: 30,
				minorSplitLine: {
					show: minorSplitLine
				},
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
					show: showXGrid,
					lineStyle: {
						color: '#e0e0e0',
						type: 'dashed'
					}
				}
			},
			yAxis: {
				type: yAxisScale === 'log' ? 'log' : 'value',
				name: yAxisLabel,
				nameLocation: 'middle',
				nameGap: 50,
				max: yAxisScale === 'log' ? undefined : autoYMax ? undefined : 1,
				axisLabel: {
					formatter: function (value: number) {
						return (value * 100).toFixed(0) + '%';
					}
				},
				splitLine: {
					show: showYGrid,
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
					symbol: 'none',
					showSymbol: false,
					lineStyle: {
						color: '#ff6b6b',
						width: 3
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
	style="height: 400px; min-width: 600px;"
></div>
