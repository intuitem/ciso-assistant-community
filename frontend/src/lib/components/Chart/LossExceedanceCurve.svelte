<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
		data?: Array<[number, number]>;
		toleranceData?: Array<[number, number]>;
		residualData?: Array<[number, number]>;
		lossThreshold?: number;
		currency?: string;
		title?: string;
		showTitle?: boolean;
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
		autoXMax?: boolean;
		enableZoom?: boolean;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = 'loss-exceedance',
		data = undefined,
		toleranceData = undefined,
		residualData = undefined,
		lossThreshold = undefined,
		currency = '€',
		title = m.lossExceedanceCurve(),
		showTitle = false,
		xAxisLabel = m.lossAmount(),
		yAxisLabel = m.exceedanceProbability(),
		minorSplitLine = false,
		enableTooltip = false,
		showXGrid = true,
		showYGrid = true,
		xMax = 1000000,
		xMin = undefined,
		autoYMax = false,
		autoXMax = false,
		xAxisScale = 'log',
		yAxisScale = 'linear',
		enableZoom = false
	}: Props = $props();

	const chart_id = `${name}_div`;

	// Helper function to calculate max loss from data arrays
	function getMaxLossFromData(
		...dataArrays: (Array<[number, number]> | undefined)[]
	): number | undefined {
		let maxLoss = 0;
		for (const dataArray of dataArrays) {
			if (dataArray && dataArray.length > 0) {
				for (const [loss] of dataArray) {
					if (loss > maxLoss) {
						maxLoss = loss;
					}
				}
			}
		}
		return maxLoss > 0 ? maxLoss : undefined;
	}

	// Calculate dynamic X-axis bounds
	const calculatedXMax = autoXMax
		? (getMaxLossFromData(data, toleranceData, residualData) ?? xMax)
		: xMax;

	// Use provided xMin or calculate from data, fallback to calculatedXMax/100000
	const calculatedXMin = xMin ?? (calculatedXMax ? calculatedXMax / 100000 : undefined);

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const option = {
			title: showTitle
				? {
						text: title,
						left: 'center',
						textStyle: {
							fontSize: 16,
							fontWeight: 'bold'
						}
					}
				: undefined,
			dataZoom: enableZoom
				? [
						{
							type: 'slider',
							xAxisIndex: 0,
							filterMode: 'none',
							bottom: 0,
							height: 30,
							showDetail: false,
							handleStyle: {
								color: '#007bff'
							},
							dataBackground: {
								areaStyle: {
									color: 'rgba(0, 123, 255, 0.1)'
								},
								lineStyle: {
									color: '#007bff'
								}
							}
						},
						{
							type: 'inside',
							xAxisIndex: 0,
							filterMode: 'none'
						}
					]
				: undefined,
			legend: {
				show:
					(toleranceData && toleranceData.length > 0) || (residualData && residualData.length > 0),
				top: '5%',
				left: '10%',
				data: [
					{
						name: m.currentRisk(),
						icon: 'circle',
						itemStyle: {
							color: '#ff6b6b'
						}
					},
					...(residualData && residualData.length > 0
						? [
								{
									name: m.residualRisk(),
									icon: 'circle',
									itemStyle: {
										color: '#007bff'
									}
								}
							]
						: []),
					...(toleranceData && toleranceData.length > 0
						? [
								{
									name: m.riskTolerance(),
									icon: 'circle',
									itemStyle: {
										color: '#28a745'
									}
								}
							]
						: [])
				]
			},
			grid: {
				show: false,
				left: '10%',
				right: '10%',
				top: '15%',
				bottom: enableZoom ? '20%' : '15%'
			},
			tooltip: {
				show: !!enableTooltip,
				trigger: 'axis',
				formatter: function (params: any) {
					if (params.length === 0) return '';

					const lossAmount = params[0].value[0];
					let tooltip = `${xAxisLabel.replace('($)', `(${currency})`)}: ${currency}${lossAmount.toLocaleString()}<br/>`;

					// Find different series
					const currentRiskParam = params.find((p: any) => p.seriesName === m.currentRisk());
					const residualRiskParam = params.find((p: any) => p.seriesName === m.residualRisk());
					const riskToleranceParam = params.find((p: any) => p.seriesName === m.riskTolerance());

					if (currentRiskParam) {
						tooltip += `${m.currentRisk()}: ${(currentRiskParam.value[1] * 100).toFixed(2)}%<br/>`;
					}

					if (residualRiskParam) {
						tooltip += `${m.residualRisk()}: ${(residualRiskParam.value[1] * 100).toFixed(2)}%<br/>`;
					}

					if (riskToleranceParam) {
						tooltip += `${m.riskTolerance()}: ${(riskToleranceParam.value[1] * 100).toFixed(2)}%<br/>`;

						// Add interpretation comparing current risk with tolerance
						if (currentRiskParam && riskToleranceParam) {
							const currentProb = currentRiskParam.value[1];
							const toleranceProb = riskToleranceParam.value[1];

							if (currentProb > toleranceProb) {
								tooltip += `<span style="color: #dc3545;">⚠️ ${m.currentRiskExceedsTolerance()}</span><br/>`;
							} else {
								tooltip += `<span style="color: #28a745;">✓ ${m.currentRiskWithinTolerance()}</span><br/>`;
							}
						}

						// Add interpretation comparing residual risk with tolerance
						if (residualRiskParam && riskToleranceParam) {
							const residualProb = residualRiskParam.value[1];
							const toleranceProb = riskToleranceParam.value[1];

							if (residualProb > toleranceProb) {
								tooltip += `<span style="color: #dc3545;">⚠️ ${m.residualRiskExceedsTolerance()}</span>`;
							} else {
								tooltip += `<span style="color: #28a745;">✓ ${m.residualRiskWithinTolerance()}</span>`;
							}
						}
					}

					return tooltip;
				}
			},
			xAxis: {
				type: xAxisScale,
				name: xAxisLabel,
				nameLocation: 'middle',
				min: calculatedXMin,
				max: calculatedXMax,
				nameGap: 30,
				minorSplitLine: {
					show: minorSplitLine
				},
				axisLabel: {
					formatter: function (value: number) {
						if (value >= 1000000000) {
							return currency + (value / 1000000000).toFixed(0) + 'B';
						} else if (value >= 1000000) {
							return currency + (value / 1000000).toFixed(0) + 'M';
						} else if (value >= 1000) {
							return currency + (value / 1000).toFixed(0) + 'K';
						} else {
							return currency + value.toFixed(0);
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
				// Combined Current Risk curve
				{
					name: m.currentRisk(),
					type: 'line',
					smooth: true,
					symbol: 'none',
					symbolSize: 0,
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
					data: data,
					...(lossThreshold !== undefined && lossThreshold > 0
						? {
								markLine: {
									silent: false,
									symbol: 'none',
									label: {
										show: true,
										position: 'end',
										formatter: `${m.lossThresholdLabel()}: ${currency}${lossThreshold.toLocaleString()}`,
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
											name: m.lossThresholdLabel()
										}
									]
								}
							}
						: {})
				},
				// Combined Residual Risk curve (only if residualData is provided)
				...(residualData && residualData.length > 0
					? [
							{
								name: m.residualRisk(),
								type: 'line',
								smooth: true,
								symbol: 'none',
								symbolSize: 0,
								showSymbol: false,
								lineStyle: {
									color: '#007bff',
									width: 3
								},
								areaStyle: {
									opacity: 0.1,
									color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
										{
											offset: 0,
											color: '#007bff'
										},
										{
											offset: 1,
											color: 'rgba(0, 123, 255, 0.05)'
										}
									])
								},
								data: residualData
							}
						]
					: []),
				// Risk tolerance curve series (only if toleranceData is provided)
				...(toleranceData && toleranceData.length > 0
					? [
							{
								name: m.riskTolerance(),
								type: 'line',
								smooth: true,
								symbol: 'none',
								symbolSize: 0,
								showSymbol: false,
								lineStyle: {
									color: '#28a745',
									width: 3,
									type: 'dashed'
								},
								data: toleranceData
							}
						]
					: [])
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
