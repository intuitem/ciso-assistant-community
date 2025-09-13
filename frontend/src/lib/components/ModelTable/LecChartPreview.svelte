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
	let currentMetaId = $state(null);

	const initializeChart = async () => {
		// cell contains the lec_data: [[x, y], [x, y], ...]
		if (!cell || !Array.isArray(cell) || cell.length === 0) {
			hasValidData = false;
			return;
		}

		// Check if this is a different row/hypothesis
		if (currentMetaId !== meta?.id) {
			currentMetaId = meta?.id;
			hasValidData = false; // Reset state for new row
		}

		hasValidData = true;
		const chartData = cell;

		// Wait for the DOM to update before initializing chart
		await new Promise((resolve) => setTimeout(resolve, 0));

		const echarts = await import('echarts');
		if (chart) {
			chart.dispose();
			chart = null;
		}

		if (!chartContainer) {
			return;
		}

		// Ensure the container is clean before initializing
		chartContainer.innerHTML = '';
		chart = echarts.init(chartContainer, null, { renderer: 'svg' });

		// Filter out zero values for logarithmic x-axis (can't display x=0 on log scale)
		const nonZeroData = chartData.filter(([x, _]: [number, number]) => x > 0);

		if (nonZeroData.length === 0) {
			console.log('No non-zero data points for logarithmic chart');
			return;
		}

		// Calculate min and max values from non-zero data
		const minFromData = Math.min(...nonZeroData.map(([x, _]: [number, number]) => x));
		const maxFromData = Math.max(...nonZeroData.map(([x, _]: [number, number]) => x));

		// Same calculation as the detail page
		const calculatedXMin = Math.max(minFromData * 0.8, 1); // Reduce by 20% but minimum of $1
		const calculatedXMax = Math.ceil(maxFromData * 1.2); // Add 20% padding

		const option = {
			grid: {
				show: false,
				left: '25%', // More space for Y-axis labels
				right: '5%',
				top: '5%',
				bottom: '20%' // More space for X-axis labels
			},
			tooltip: {
				show: false // Disable tooltip for small preview
			},
			xAxis: {
				type: 'log', // Same as LossExceedanceCurve default
				min: calculatedXMin,
				max: calculatedXMax,
				axisLabel: {
					formatter: function (value: number) {
						if (value >= 1000000000) {
							return (value / 1000000000).toFixed(0) + 'B';
						} else if (value >= 1000000) {
							return (value / 1000000).toFixed(0) + 'M';
						} else if (value >= 1000) {
							return (value / 1000).toFixed(0) + 'K';
						} else {
							return value.toFixed(0);
						}
					},
					fontSize: 8
				},
				splitLine: {
					show: false
				}
			},
			yAxis: {
				type: 'value', // Same as LossExceedanceCurve (linear scale)
				max: undefined, // Auto-adjust like LossExceedanceCurve with autoYMax
				axisLabel: {
					formatter: function (value: number) {
						return (value * 100).toFixed(0) + '%';
					},
					fontSize: 8
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
					data: nonZeroData
				}
			]
		};

		chart.setOption(option);
	};

	onMount(async () => {
		await initializeChart();
	});

	// React to data changes (when table is sorted/filtered)
	$effect(() => {
		// This will run whenever cell or meta changes
		if (cell && meta) {
			// Dispose existing chart first to prevent mixing
			if (chart) {
				chart.dispose();
				chart = null;
			}
			initializeChart();
		}
	});

	// Cleanup on unmount
	onMount(() => {
		return () => {
			if (chart) {
				chart.dispose();
				chart = null;
			}
		};
	});
</script>

{#if hasValidData}
	<div bind:this={chartContainer} class="h-24 w-32 min-w-[128px]"></div>
{:else}
	<div
		class="h-24 w-32 min-w-[128px] flex items-center justify-center text-gray-500 text-xs bg-gray-50 rounded"
	>
		No simulation
	</div>
{/if}
