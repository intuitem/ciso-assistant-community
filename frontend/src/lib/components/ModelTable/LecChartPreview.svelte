<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		cell: any;
		meta: any;
	}

	let { cell, meta }: Props = $props();

	let chartContainer: HTMLDivElement;
	let chart: any;
	let hasValidData = $state(false);

	const initializeChart = async () => {
		// cell contains the lec_data: [[x, y], [x, y], ...]
		if (!cell || !Array.isArray(cell) || cell.length === 0) {
			return;
		}

		hasValidData = true;
		const chartData = cell;

		// Wait for the DOM to update before initializing chart
		await new Promise(resolve => setTimeout(resolve, 0));

		const echarts = await import('echarts');
		if (chart) {
			chart.dispose();
		}

		if (!chartContainer) {
			return;
		}

		chart = echarts.init(chartContainer, null, { renderer: 'svg' });

		// Calculate min and max values from the data
		const minValue = Math.min(...chartData.map(([x, _]: [number, number]) => x));
		const maxValue = Math.max(...chartData.map(([x, _]: [number, number]) => x));
		const calculatedXMin = Math.max(minValue * 0.8, 1);
		const calculatedXMax = Math.ceil(maxValue * 1.2);

		const option = {
			grid: {
				left: '15%',
				right: '10%',
				top: '10%',
				bottom: '15%'
			},
			tooltip: {
				trigger: 'axis',
				formatter: function (params: any) {
					const point = params[0];
					return `Loss: $${point.value[0].toLocaleString()}<br/>Probability: ${(point.value[1] * 100).toFixed(2)}%`;
				}
			},
			xAxis: {
				type: 'log',
				min: calculatedXMin,
				max: calculatedXMax,
				axisLabel: {
					formatter: function (value: number) {
						if (value >= 1000000) {
							return '$' + (value / 1000000).toFixed(0) + 'M';
						} else if (value >= 1000) {
							return '$' + (value / 1000).toFixed(0) + 'K';
						} else {
							return '$' + value.toFixed(0);
						}
					},
					fontSize: 10
				},
				splitLine: {
					show: false
				}
			},
			yAxis: {
				type: 'value',
				max: 1,
				axisLabel: {
					formatter: function (value: number) {
						return (value * 100).toFixed(0) + '%';
					},
					fontSize: 10
				},
				splitLine: {
					show: false
				}
			},
			series: [
				{
					type: 'line',
					smooth: true,
					symbol: 'none',
					lineStyle: {
						color: '#ff6b6b',
						width: 2
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
					data: chartData
				}
			]
		};

		chart.setOption(option);
	};

	onMount(async () => {
		await initializeChart();
	});

	// Cleanup on unmount
	onMount(() => {
		return () => {
			if (chart) {
				chart.dispose();
			}
		};
	});
</script>

{#if hasValidData}
	<div bind:this={chartContainer} class="h-24 w-32 min-w-[128px]"></div>
{:else}
	<div class="h-24 w-32 min-w-[128px] flex items-center justify-center text-gray-500 text-xs bg-gray-50 rounded">
		No simulation
	</div>
{/if}
