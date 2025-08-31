<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
		lowerBound?: number;
		upperBound?: number;
		title?: string;
		xAxisLabel?: string;
		yAxisLabel?: string;
		enableTooltip?: boolean;
		xAxisScale?: 'linear' | 'log';
		onParametersCalculated?: (mu: number, sigma: number) => void;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = 'lognormal-distribution',
		lowerBound = 1000,
		upperBound = 10000,
		title = 'Impact Distribution (90% CI)',
		xAxisLabel = 'Loss Amount ($)',
		yAxisLabel = 'Probability Density',
		enableTooltip = true,
		xAxisScale = 'linear',
		onParametersCalculated = undefined
	}: Props = $props();

	const chart_id = `${name}_div`;

	// Calculate lognormal parameters from 90% CI bounds
	function calculateLognormalParams(lb: number, ub: number) {
		const z05 = -1.64485362695147; // 5th percentile
		const z95 = 1.64485362695147; // 95th percentile
		const ln_lb = Math.log(lb);
		const ln_ub = Math.log(ub);
		const sigma = (ln_ub - ln_lb) / (z95 - z05);
		const mu = ln_lb - sigma * z05;
		return { mu, sigma };
	}

	// Generate lognormal probability density values
	function generateLognormalPDF(
		mu: number,
		sigma: number,
		xMin: number,
		xMax: number,
		scale: 'linear' | 'log' = 'linear',
		points: number = 500
	) {
		const data = [];

		if (scale === 'log') {
			// For log scale, use log-spaced points for better visualization
			const logXMin = Math.log(Math.max(xMin, 1));
			const logXMax = Math.log(xMax);

			for (let i = 0; i <= points; i++) {
				const logX = logXMin + (i / points) * (logXMax - logXMin);
				const x = Math.exp(logX);

				// Lognormal PDF
				const lnX = Math.log(x);
				const pdf =
					(1 / (x * sigma * Math.sqrt(2 * Math.PI))) *
					Math.exp(-Math.pow(lnX - mu, 2) / (2 * sigma * sigma));

				data.push([x, pdf]);
			}
		} else {
			// For linear scale, use linear-spaced points
			for (let i = 0; i <= points; i++) {
				const x = xMin + (i / points) * (xMax - xMin);

				if (x <= 0) continue; // Lognormal only defined for x > 0

				// Lognormal PDF
				const lnX = Math.log(x);
				const pdf =
					(1 / (x * sigma * Math.sqrt(2 * Math.PI))) *
					Math.exp(-Math.pow(lnX - mu, 2) / (2 * sigma * sigma));

				data.push([x, pdf]);
			}
		}
		return data;
	}

	onMount(async () => {
		if (!lowerBound || !upperBound || lowerBound >= upperBound) {
			return;
		}

		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const { mu, sigma } = calculateLognormalParams(lowerBound, upperBound);

		// Verify our calculation by checking if the percentiles match
		const calculated5th = Math.exp(mu + sigma * -1.64485362695147);
		const calculated95th = Math.exp(mu + sigma * 1.64485362695147);
		console.log(
			`Verification - Input: ${lowerBound}-${upperBound}, Calculated: ${calculated5th.toFixed(0)}-${calculated95th.toFixed(0)}`
		);

		// Call the callback with calculated parameters
		if (onParametersCalculated) {
			onParametersCalculated(mu, sigma);
		}

		// Use a more reasonable range: from 10% of lower bound to 10x upper bound
		const chartMin = Math.max(lowerBound * 0.1, 1);
		const chartMax = upperBound * 5;
		const distributionData = generateLognormalPDF(mu, sigma, chartMin, chartMax, xAxisScale);

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
					const value = point.value[0];
					const density = point.value[1];
					let formattedValue;
					if (value >= 1000000) {
						formattedValue = `$${(value / 1000000).toFixed(1)}M`;
					} else if (value >= 1000) {
						formattedValue = `$${(value / 1000).toFixed(0)}K`;
					} else {
						formattedValue = `$${value.toFixed(0)}`;
					}
					return `${xAxisLabel}: ${formattedValue}<br/>${yAxisLabel}: ${density.toExponential(3)}`;
				}
			},
			xAxis: {
				type: xAxisScale === 'log' ? 'log' : 'value',
				name: xAxisLabel,
				nameLocation: 'middle',
				nameGap: 30,
				min: chartMin,
				max: chartMax,
				axisLabel: {
					formatter: function (value: number) {
						if (value >= 1000000) {
							return '$' + (value / 1000000).toFixed(1) + 'M';
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
				axisLabel: {
					formatter: function (value: number) {
						if (value === 0) return '0';
						return value.toExponential(1);
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
					name: 'Impact Distribution',
					type: 'line',
					smooth: true,
					symbol: 'none',
					showSymbol: false,
					lineStyle: {
						color: '#4f46e5',
						width: 3
					},
					areaStyle: {
						opacity: 0.2,
						color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
							{
								offset: 0,
								color: '#4f46e5'
							},
							{
								offset: 1,
								color: 'rgba(79, 70, 229, 0.05)'
							}
						])
					},
					data: distributionData,
					// Add vertical lines for 5th and 95th percentiles
					markLine: {
						silent: true,
						symbol: 'none',
						lineStyle: {
							color: '#dc2626',
							type: 'dashed',
							width: 2
						},
						label: {
							show: true,
							position: 'end',
							formatter: function (params: any) {
								const value = params.value;
								if (value >= 1000000) {
									return `$${(value / 1000000).toFixed(1)}M`;
								} else if (value >= 1000) {
									return `$${(value / 1000).toFixed(0)}K`;
								} else {
									return `$${value.toFixed(0)}`;
								}
							}
						},
						data: [
							{ xAxis: lowerBound, label: { formatter: '5th %ile: {c}' } },
							{ xAxis: upperBound, label: { formatter: '95th %ile: {c}' } }
						]
					}
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
