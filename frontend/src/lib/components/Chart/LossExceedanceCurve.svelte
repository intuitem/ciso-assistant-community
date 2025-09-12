<script lang="ts">
	import { onMount } from 'svelte';

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
		currency = '$',
		title = 'Loss Exceedance Curve',
		showTitle = true,
		xAxisLabel = 'Loss Amount',
		yAxisLabel = 'Exceedance Probability',
		minorSplitLine = false,
		enableTooltip = false,
		showXGrid = true,
		showYGrid = true,
		xMax = 1000000,
		xMin = undefined,
		autoYMax = false,
		xAxisScale = 'log',
		yAxisScale = 'linear'
	}: Props = $props();

	const chart_id = `${name}_div`;

	// Use provided xMin or calculate from data, fallback to xMax/100000
	const calculatedXMin = xMin ?? (xMax ? xMax / 100000 : undefined);

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
			legend: {
				show:
					(toleranceData && toleranceData.length > 0) || (residualData && residualData.length > 0),
				top: '5%',
				left: '10%',
				data: [
					{
						name: 'Current Risk',
						icon: 'circle',
						itemStyle: {
							color: '#ff6b6b'
						}
					},
					...(residualData && residualData.length > 0
						? [
								{
									name: 'Residual Risk',
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
									name: 'Risk Tolerance',
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
				bottom: '15%'
			},
			tooltip: {
				show: !!enableTooltip,
				trigger: 'axis',
				formatter: function (params: any) {
					if (params.length === 0) return '';

					const lossAmount = params[0].value[0];
					let tooltip = `${xAxisLabel.replace('($)', `(${currency})`)}: ${currency}${lossAmount.toLocaleString()}<br/>`;

					// Find different series
					const currentRiskParam = params.find((p: any) => p.seriesName === 'Current Risk');
					const residualRiskParam = params.find((p: any) => p.seriesName === 'Residual Risk');
					const riskToleranceParam = params.find((p: any) => p.seriesName === 'Risk Tolerance');

					if (currentRiskParam) {
						tooltip += `Current Risk: ${(currentRiskParam.value[1] * 100).toFixed(2)}%<br/>`;
					}

					if (residualRiskParam) {
						tooltip += `Residual Risk: ${(residualRiskParam.value[1] * 100).toFixed(2)}%<br/>`;
					}

					if (riskToleranceParam) {
						tooltip += `Risk Tolerance: ${(riskToleranceParam.value[1] * 100).toFixed(2)}%<br/>`;

						// Add interpretation comparing current risk with tolerance
						if (currentRiskParam && riskToleranceParam) {
							const currentProb = currentRiskParam.value[1];
							const toleranceProb = riskToleranceParam.value[1];

							if (currentProb > toleranceProb) {
								tooltip +=
									'<span style="color: #dc3545;">⚠️ Current risk exceeds tolerance</span><br/>';
							} else {
								tooltip +=
									'<span style="color: #28a745;">✓ Current risk within tolerance</span><br/>';
							}
						}

						// Add interpretation comparing residual risk with tolerance
						if (residualRiskParam && riskToleranceParam) {
							const residualProb = residualRiskParam.value[1];
							const toleranceProb = riskToleranceParam.value[1];

							if (residualProb > toleranceProb) {
								tooltip +=
									'<span style="color: #dc3545;">⚠️ Residual risk exceeds tolerance</span>';
							} else {
								tooltip += '<span style="color: #28a745;">✓ Residual risk within tolerance</span>';
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
				max: xMax,
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
					name: 'Current Risk',
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
								}
							}
						: {})
				},
				// Combined Residual Risk curve (only if residualData is provided)
				...(residualData && residualData.length > 0
					? [
							{
								name: 'Residual Risk',
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
								name: 'Risk Tolerance',
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
