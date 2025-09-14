<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { onMount } from 'svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	onMount(async () => {
		if (data.lec?.curves?.length > 0) {
			//temporary embedded chart for now
			const echarts = await import('echarts');
			const chart = echarts.init(document.getElementById('combined-lec-chart'));

			const currency = data.lec.currency || '€';
			const lossThreshold = data.lec.loss_threshold;

			const series = data.lec.curves.map((curve: any, index: number) => {
				// Define specific styling for current risk and risk tolerance curves
				let lineStyle: any = { width: 3 };
				let itemStyle: any = {};
				let markLine: any = {};

				if (curve.name === 'Current Risk' || curve.name === 'Combined Current Risk') {
					// Current risk: bold red line
					lineStyle = {
						width: 4,
						color: '#FF6367',
						type: 'solid'
					};
					itemStyle = {
						color: '#FF6367'
					};

					// Add loss threshold line to the first current risk curve
					if (lossThreshold && lossThreshold > 0) {
						markLine = {
							silent: false,
							symbol: 'none',
							label: {
								show: true,
								position: 'end',
								formatter: `Loss Threshold: ${currency}${lossThreshold.toLocaleString()}`,
								fontSize: 12,
								color: '#7c3aed',
								backgroundColor: 'rgba(255, 255, 255, 0.9)',
								borderColor: '#7c3aed',
								borderWidth: 1,
								borderRadius: 4,
								padding: [4, 8]
							},
							lineStyle: {
								color: '#7c3aed',
								width: 2,
								type: 'dashed'
							},
							data: [
								{
									xAxis: lossThreshold,
									name: 'Loss Threshold'
								}
							]
						};
					}
				} else if (curve.name === 'Risk Tolerance') {
					// Risk tolerance: dashed orange line
					lineStyle = {
						width: 3,
						color: '#7CCF00',
						type: 'dashed'
					};
					itemStyle = {
						color: '#7CCF00'
					};
				}

				const seriesConfig: any = {
					name: curve.name,
					type: 'line',
					data: curve.data,
					smooth: true,
					symbol: 'none',
					lineStyle,
					itemStyle
				};

				// Add markLine only if it has data
				if (markLine.data) {
					seriesConfig.markLine = markLine;
				}

				return seriesConfig;
			});

			const option = {
				tooltip: {
					show: true,
					trigger: 'axis',
					backgroundColor: 'rgba(255, 255, 255, 0.95)',
					borderColor: '#ddd',
					borderWidth: 1,
					textStyle: {
						color: '#333'
					},
					formatter: function (params: any) {
						if (params.length === 0) return '';

						const lossAmount = params[0].value[0];
						let tooltip = `Loss Amount: ${currency}${lossAmount.toLocaleString()}<br/>`;

						// Add each curve's probability value
						params.forEach((param: any) => {
							const probability = param.value[1];
							const percentageDisplay = (probability * 100).toFixed(2);

							// Use different colors for different curve types
							let color = param.color;
							if (
								param.seriesName === 'Current Risk' ||
								param.seriesName === 'Combined Current Risk'
							) {
								color = '#FF6367';
							} else if (param.seriesName === 'Risk Tolerance') {
								color = '#7CCF00';
							}

							tooltip += `<span style="color: ${color};">●</span> ${param.seriesName}: ${percentageDisplay}%<br/>`;
						});

						return tooltip;
					}
				},
				legend: {
					top: 0,
					data: data.lec.curves.map((curve: any) => ({
						name: curve.name,
						icon: 'circle'
					}))
				},
				grid: {
					left: '10%',
					right: '10%',
					top: '15%',
					bottom: '15%'
				},
				xAxis: {
					type: 'log',
					name: `Loss Amount (${currency})`,
					nameLocation: 'middle',
					nameGap: 30,
					axisLabel: {
						formatter: (value: number) => {
							if (value >= 1000000) return currency + (value / 1000000).toFixed(0) + 'M';
							if (value >= 1000) return currency + (value / 1000).toFixed(0) + 'K';
							return currency + value.toFixed(0);
						}
					}
				},
				yAxis: {
					type: 'value',
					name: 'Exceedance Probability',
					nameLocation: 'middle',
					nameGap: 50,
					axisLabel: {
						formatter: (value: number) => (value * 100).toFixed(0) + '%'
					}
				},
				series: series
			};

			chart.setOption(option);

			window.addEventListener('resize', () => chart.resize());
		}
	});

</script>

<DetailView {data}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4 bg-slate-100 rounded-xl p-4">
			{#if data.lec?.curves?.length > 0}
				<!-- Multi-Curve LEC Chart -->
				<div class="bg-white rounded-lg p-4 shadow-sm w-full">
					<h5 class="text-lg font-semibold text-gray-700 mb-4">Compare hypotheses</h5>
					<div id="combined-lec-chart" style="height: 400px; width: 100%;"></div>
				</div>
			{:else}
				<!-- Empty State -->
				<div class="bg-white rounded-lg p-8 shadow-sm text-center">
					<div class="flex flex-col items-center space-y-4">
						<i class="fa-solid fa-chart-area text-4xl text-gray-400"></i>
						<h5 class="text-lg font-semibold text-gray-600">Loss Exceedance Curves</h5>
						<p class="text-gray-500">
							No curve data available. Run simulations on your hypotheses to generate LEC charts.
						</p>
					</div>
				</div>
			{/if}
		</div>
	{/snippet}
</DetailView>
