<script lang="ts">
	import { onMount } from 'svelte';

	interface ScenarioData {
		name: string;
		currentALE: number | null;
		residualALE: number | null;
		treatmentCost: number | null;
	}

	interface Props {
		scenarios: ScenarioData[];
		title?: string;
		width?: string;
		height?: string;
		classesContainer?: string;
	}

	let {
		scenarios,
		title = 'ALE Comparison by Scenario',
		width = 'w-auto',
		height = 'h-96',
		classesContainer = ''
	}: Props = $props();

	const chart_id = `ale_comparison_${Math.random().toString(36).substr(2, 9)}`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// Prepare data for the chart
		const scenarioNames = scenarios.map((s) => s.name);
		const currentALEData = scenarios.map((s) => s.currentALE || 0);
		const residualALEData = scenarios.map((s) => s.residualALE || 0);
		const treatmentCostData = scenarios.map((s) => -(s.treatmentCost || 0)); // Negative for below zero

		// Custom formatter for currency values
		const formatCurrency = (value: number) => {
			const absValue = Math.abs(value);
			if (absValue >= 1_000_000) {
				return `${(value / 1_000_000).toFixed(1)}M €`;
			} else if (absValue >= 1_000) {
				return `${(value / 1_000).toFixed(0)}K €`;
			} else {
				return `${value.toFixed(0)} €`;
			}
		};

		const option = {
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow'
				},
				formatter: function (params: any) {
					let result = `<div><strong>${params[0].axisValue}</strong></div>`;
					params.forEach((param: any) => {
						const value = Math.abs(param.value);
						const sign = param.value >= 0 ? '' : '-';
						result += `<div style="color: ${param.color};">
							${param.marker} ${param.seriesName}: ${sign}${formatCurrency(value)}
						</div>`;
					});
					return result;
				}
			},
			legend: {
				data: ['Current ALE', 'Residual ALE', 'Treatment Cost'],
				bottom: 0
			},
			grid: {
				left: 60,
				right: 60,
				bottom: 60,
				top: 40,
				containLabel: true
			},
			xAxis: {
				type: 'category',
				data: scenarioNames,
				axisLabel: {
					interval: 0,
					rotate: scenarioNames.length > 5 ? 45 : 0
				}
			},
			yAxis: {
				type: 'value',
				axisLabel: {
					formatter: formatCurrency
				},
				splitLine: {
					lineStyle: {
						type: 'dashed'
					}
				}
			},
			series: [
				{
					name: 'Current ALE',
					type: 'bar',
					data: currentALEData,
					itemStyle: {
						color: '#e07a5f'
					},
					emphasis: {
						itemStyle: {
							color: '#dc2626'
						}
					}
				},
				{
					name: 'Residual ALE',
					type: 'bar',
					data: residualALEData,
					itemStyle: {
						color: '#f2cc8f'
					},
					emphasis: {
						itemStyle: {
							color: '#ea580c'
						}
					}
				},
				{
					name: 'Treatment Cost',
					type: 'bar',
					data: treatmentCostData,
					itemStyle: {
						color: '#3d405b' // Blue for costs (negative values)
					},
					emphasis: {
						itemStyle: {
							color: '#2563eb'
						}
					}
				}
			]
		};

		chart.setOption(option);

		// Handle window resize
		const handleResize = () => {
			chart.resize();
		};
		window.addEventListener('resize', handleResize);

		// Cleanup function
		return () => {
			window.removeEventListener('resize', handleResize);
			chart.dispose();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
