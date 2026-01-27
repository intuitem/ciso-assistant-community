<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
		value: number;
		max: number;
		isPercentage?: boolean;
		color?: string;
		backgroundColor?: string;
		strokeWidth?: number;
		fontSize?: number;
		title?: string;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = 'single_gauge',
		value,
		max,
		isPercentage = false,
		color = '#B075CC',
		backgroundColor = '#E6E6E6',
		strokeWidth = 20,
		fontSize = 32,
		title = ''
	}: Props = $props();

	const chart_id = `${name}_${crypto.randomUUID().slice(0, 8)}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		const el = document.getElementById(chart_id);
		if (!el) return;
		const chart = echarts.init(el, null, { renderer: 'svg' });

		// Capture values at mount time to avoid reactive context issues in ECharts callbacks
		const percentage = max > 0 ? (value / max) * 100 : 0;
		const displayValue = Math.round(value * 10) / 10;

		const option = {
			title: {
				text: title,
				textStyle: {
					fontWeight: 'bold',
					fontSize: 14
				}
			},
			series: [
				{
					type: 'gauge',
					radius: '65%',
					center: ['50%', '45%'],
					startAngle: 90,
					endAngle: -270,
					min: 0,
					max: 100,
					pointer: {
						show: false
					},
					progress: {
						show: true,
						width: strokeWidth,
						roundCap: true,
						itemStyle: {
							color: color
						}
					},
					axisLine: {
						lineStyle: {
							width: strokeWidth,
							color: [[1, backgroundColor]]
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
					title: {
						show: false
					},
					data: [
						{
							value: percentage,
							detail: {
								valueAnimation: true,
								offsetCenter: ['0%', '0%'],
								fontSize: fontSize,
								fontWeight: 'bold',
								color: '#333',
								formatter: function () {
									return isPercentage ? `${displayValue}%` : displayValue;
								}
							}
						}
					],
					detail: {
						width: 80,
						height: 60,
						fontSize: fontSize,
						fontWeight: 'bold',
						color: '#333',
						backgroundColor: 'transparent',
						borderWidth: 0
					}
				}
			]
		};

		chart.setOption(option);

		const handleResize = () => chart.resize();
		window.addEventListener('resize', handleResize);

		return () => {
			window.removeEventListener('resize', handleResize);
			chart.dispose();
		};
	});
</script>

<div
	id={chart_id}
	class="{width} {height} {classesContainer}"
	style="min-width: 180px; min-height: 180px;"
	data-testid="progress-ring-svg"
	aria-valuenow={value}
	aria-valuemax={max}
	role="progressbar"
></div>
