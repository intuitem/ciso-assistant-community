<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		samples?: any[];
		metricDefinition?: any;
		width?: string;
		height?: string;
		classesContainer?: string;
	}

	let {
		samples = [],
		metricDefinition = null,
		width = 'w-full',
		height = 'h-96',
		classesContainer = ''
	}: Props = $props();

	const chart_id = `metric-sample-chart-${crypto.randomUUID()}`;
	const isQualitative = $derived(metricDefinition?.category === 'qualitative');
	const unitName = $derived(metricDefinition?.unit?.name || '');
	// Display symbol for unit (e.g., '%' instead of 'percentage')
	const unitSymbol = $derived(unitName === 'percentage' ? '%' : unitName);

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// Prepare data from samples
		const chartData = samples
			.map((sample) => {
				try {
					const value = typeof sample.value === 'string' ? JSON.parse(sample.value) : sample.value;
					if (isQualitative) {
						// For qualitative: extract choice_index
						return [sample.timestamp, value?.choice_index ?? null];
					} else {
						// For quantitative: extract result
						return [sample.timestamp, value?.result ?? null];
					}
				} catch {
					return [sample.timestamp, null];
				}
			})
			.filter((item) => item[1] !== null)
			.sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime());

		// Get choice names for qualitative metrics
		const choiceNames = isQualitative
			? metricDefinition?.choices_definition?.map((c) => c.name)
			: [];

		const option = {
			grid: {
				top: 40,
				right: 40,
				bottom: 60,
				left: 60
			},
			tooltip: {
				trigger: 'axis',
				formatter: function (params) {
					const date = new Date(params[0].value[0]).toLocaleString();
					const value = params[0].value[1];
					let displayValue = value;

					if (isQualitative && choiceNames && choiceNames[value - 1]) {
						displayValue = `${value}. ${choiceNames[value - 1]}`;
					} else if (!isQualitative && unitSymbol) {
						displayValue = unitName === 'percentage' ? `${value}%` : `${value} ${unitSymbol}`;
					}

					return `${date}<br/>${params[0].marker}${params[0].seriesName}: ${displayValue}`;
				}
			},
			xAxis: {
				type: 'time',
				axisLabel: {
					formatter: function (value) {
						return new Date(value).toLocaleDateString();
					}
				}
			},
			yAxis: {
				type: 'value',
				name: isQualitative ? m.choiceLevel() : unitSymbol,
				nameLocation: 'middle',
				nameGap: 50,
				...(isQualitative && choiceNames.length > 0
					? {
							min: 1,
							max: choiceNames.length,
							interval: 1,
							axisLabel: {
								formatter: function (value) {
									return choiceNames[value - 1] ? `${value}. ${choiceNames[value - 1]}` : '';
								}
							}
						}
					: {
							min: 0
						})
			},
			series: [
				{
					name: m.value(),
					type: 'line',
					smooth: true,
					symbol: 'circle',
					symbolSize: 8,
					areaStyle: {
						opacity: 0.3,
						color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
							{
								offset: 0,
								color: 'rgb(59, 130, 246)'
							},
							{
								offset: 1,
								color: 'rgba(59, 130, 246, 0.1)'
							}
						])
					},
					lineStyle: {
						width: 2,
						color: 'rgb(59, 130, 246)'
					},
					itemStyle: {
						color: 'rgb(59, 130, 246)'
					},
					data: chartData
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

{#if samples.length > 0}
	<div id={chart_id} class="{height} {width} {classesContainer}"></div>
{:else}
	<div class="flex items-center justify-center {height} {width} bg-gray-50 rounded-lg">
		<p class="text-gray-500 text-sm">{m.noDataAvailable()}</p>
	</div>
{/if}
