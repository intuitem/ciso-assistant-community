<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		widget: any;
		samples?: any[];
		height?: string;
	}

	let { widget, samples = [], height = 'h-full' }: Props = $props();

	const chartId = $derived(`widget-chart-${widget.id}`);
	const metricDefinition = $derived(widget.metric_instance?.metric_definition);
	const isQualitative = $derived(metricDefinition?.category === 'qualitative');
	const unitName = $derived(metricDefinition?.unit?.name || '');
	const targetValue = $derived(widget.metric_instance?.target_value);

	// Prepare chart data from samples
	const chartData = $derived(
		samples
			.map((sample) => {
				try {
					const value = typeof sample.value === 'string' ? JSON.parse(sample.value) : sample.value;
					if (isQualitative) {
						return [sample.timestamp, value?.choice_index ?? null];
					} else {
						return [sample.timestamp, value?.result ?? null];
					}
				} catch {
					return [sample.timestamp, null];
				}
			})
			.filter((item) => item[1] !== null)
			.sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime())
	);

	// Get choice names for qualitative metrics
	const choiceNames = $derived(
		isQualitative ? metricDefinition?.choices_definition?.map((c: any) => c.name) || [] : []
	);

	// Get latest value for KPI/Gauge
	const latestValue = $derived(chartData.length > 0 ? chartData[chartData.length - 1][1] : null);

	let chartInstance: any = null;

	onMount(async () => {
		if (widget.chart_type === 'kpi_card' || widget.chart_type === 'table') {
			return; // These don't use ECharts
		}

		const echarts = await import('echarts');
		const container = document.getElementById(chartId);
		if (!container) return;

		chartInstance = echarts.init(container, null, { renderer: 'svg' });

		const option = getChartOption(echarts);
		chartInstance.setOption(option);

		const resizeHandler = () => chartInstance?.resize();
		window.addEventListener('resize', resizeHandler);

		// Use ResizeObserver for container size changes
		const resizeObserver = new ResizeObserver(() => {
			chartInstance?.resize();
		});
		resizeObserver.observe(container);

		return () => {
			window.removeEventListener('resize', resizeHandler);
			resizeObserver.disconnect();
			chartInstance?.dispose();
		};
	});

	function getChartOption(echarts: any) {
		const baseGrid = {
			top: 30,
			right: 20,
			bottom: 40,
			left: 50
		};

		const baseTooltip = {
			trigger: 'axis',
			formatter: function (params: any) {
				const date = new Date(params[0].value[0]).toLocaleString();
				const value = params[0].value[1];
				let displayValue = value;

				if (isQualitative && choiceNames && choiceNames[value - 1]) {
					displayValue = `${value}. ${choiceNames[value - 1]}`;
				} else if (!isQualitative && unitName) {
					displayValue = `${value} ${unitName}`;
				}

				return `${date}<br/>${params[0].marker}${displayValue}`;
			}
		};

		const baseXAxis = {
			type: 'time',
			axisLabel: {
				formatter: function (value: number) {
					return new Date(value).toLocaleDateString();
				}
			}
		};

		const baseYAxis = {
			type: 'value',
			name: isQualitative ? '' : unitName,
			nameLocation: 'middle',
			nameGap: 40,
			...(isQualitative && choiceNames.length > 0
				? {
						min: 1,
						max: choiceNames.length,
						interval: 1,
						axisLabel: {
							formatter: function (value: number) {
								return choiceNames[value - 1] || '';
							}
						}
					}
				: { min: 0 })
		};

		switch (widget.chart_type) {
			case 'line':
				return {
					grid: baseGrid,
					tooltip: baseTooltip,
					xAxis: baseXAxis,
					yAxis: baseYAxis,
					series: [
						{
							type: 'line',
							smooth: true,
							symbol: 'circle',
							symbolSize: 6,
							lineStyle: { width: 2, color: 'rgb(59, 130, 246)' },
							itemStyle: { color: 'rgb(59, 130, 246)' },
							data: chartData,
							...(widget.show_target && targetValue
								? {
										markLine: {
											data: [{ yAxis: targetValue, name: m.target() }],
											lineStyle: { color: 'rgb(34, 197, 94)', type: 'dashed' },
											label: { formatter: `${m.target()}: ${targetValue}` }
										}
									}
								: {})
						}
					]
				};

			case 'area':
				return {
					grid: baseGrid,
					tooltip: baseTooltip,
					xAxis: baseXAxis,
					yAxis: baseYAxis,
					series: [
						{
							type: 'line',
							smooth: true,
							symbol: 'circle',
							symbolSize: 6,
							areaStyle: {
								opacity: 0.4,
								color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
									{ offset: 0, color: 'rgb(59, 130, 246)' },
									{ offset: 1, color: 'rgba(59, 130, 246, 0.1)' }
								])
							},
							lineStyle: { width: 2, color: 'rgb(59, 130, 246)' },
							itemStyle: { color: 'rgb(59, 130, 246)' },
							data: chartData,
							...(widget.show_target && targetValue
								? {
										markLine: {
											data: [{ yAxis: targetValue, name: m.target() }],
											lineStyle: { color: 'rgb(34, 197, 94)', type: 'dashed' },
											label: { formatter: `${m.target()}: ${targetValue}` }
										}
									}
								: {})
						}
					]
				};

			case 'bar':
				return {
					grid: baseGrid,
					tooltip: {
						...baseTooltip,
						trigger: 'axis',
						axisPointer: { type: 'shadow' }
					},
					xAxis: {
						type: 'category',
						data: chartData.map((d) => new Date(d[0]).toLocaleDateString()),
						axisLabel: { rotate: 45 }
					},
					yAxis: baseYAxis,
					series: [
						{
							type: 'bar',
							data: chartData.map((d) => d[1]),
							itemStyle: {
								color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
									{ offset: 0, color: 'rgb(59, 130, 246)' },
									{ offset: 1, color: 'rgb(37, 99, 235)' }
								]),
								borderRadius: [4, 4, 0, 0]
							},
							...(widget.show_target && targetValue
								? {
										markLine: {
											data: [{ yAxis: targetValue, name: m.target() }],
											lineStyle: { color: 'rgb(34, 197, 94)', type: 'dashed' },
											label: { formatter: `${m.target()}: ${targetValue}` }
										}
									}
								: {})
						}
					]
				};

			case 'gauge':
				const maxValue = targetValue ? targetValue * 1.5 : 100;
				const gaugeValue = latestValue || 0;
				return {
					series: [
						{
							type: 'gauge',
							startAngle: 200,
							endAngle: -20,
							min: 0,
							max: maxValue,
							splitNumber: 5,
							center: ['50%', '60%'],
							radius: '90%',
							itemStyle: {
								color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
									{ offset: 0, color: 'rgb(59, 130, 246)' },
									{ offset: 0.5, color: 'rgb(34, 197, 94)' },
									{ offset: 1, color: 'rgb(239, 68, 68)' }
								])
							},
							progress: {
								show: true,
								width: 20
							},
							pointer: {
								show: true,
								length: '60%',
								width: 6
							},
							axisLine: {
								lineStyle: {
									width: 20,
									color: [[1, 'rgba(200, 200, 200, 0.3)']]
								}
							},
							axisTick: { show: false },
							splitLine: { show: false },
							axisLabel: {
								distance: 30,
								fontSize: 10
							},
							title: {
								show: true,
								offsetCenter: [0, '80%'],
								fontSize: 12
							},
							detail: {
								valueAnimation: true,
								formatter: unitName ? `{value} ${unitName}` : '{value}',
								fontSize: 20,
								offsetCenter: [0, '40%']
							},
							data: [
								{
									value: gaugeValue,
									name: widget.show_target && targetValue ? `${m.target()}: ${targetValue}` : ''
								}
							]
						}
					]
				};

			case 'sparkline':
				return {
					grid: { top: 5, right: 5, bottom: 5, left: 5 },
					xAxis: { type: 'category', show: false, data: chartData.map((d) => d[0]) },
					yAxis: { type: 'value', show: false },
					series: [
						{
							type: 'line',
							smooth: true,
							symbol: 'none',
							lineStyle: { width: 2, color: 'rgb(59, 130, 246)' },
							areaStyle: {
								opacity: 0.2,
								color: 'rgb(59, 130, 246)'
							},
							data: chartData.map((d) => d[1])
						}
					]
				};

			default:
				return {};
		}
	}

	// Format display value
	function formatValue(value: any): string {
		if (value === null || value === undefined) return 'N/A';
		if (isQualitative && choiceNames[value - 1]) {
			return `[${value}] ${choiceNames[value - 1]}`;
		}
		if (unitName === 'percentage') return `${value}%`;
		if (unitName) return `${value} ${unitName}`;
		return String(value);
	}
</script>

{#if widget.chart_type === 'kpi_card'}
	<!-- KPI Card -->
	<div class="flex items-center justify-center h-full">
		<div class="text-center">
			<div class="text-4xl font-bold text-primary-600">
				{formatValue(latestValue)}
			</div>
			{#if widget.show_target && targetValue}
				<div class="text-sm text-gray-500 mt-2">
					{m.target()}: {targetValue}
				</div>
			{/if}
			{#if chartData.length > 1}
				{@const prevValue = chartData[chartData.length - 2]?.[1]}
				{@const change = prevValue ? ((latestValue - prevValue) / prevValue * 100).toFixed(1) : null}
				{#if change !== null}
					<div class="text-sm mt-1 {Number(change) >= 0 ? 'text-green-600' : 'text-red-600'}">
						{Number(change) >= 0 ? '+' : ''}{change}%
					</div>
				{/if}
			{/if}
		</div>
	</div>
{:else if widget.chart_type === 'table'}
	<!-- Table -->
	<div class="overflow-auto h-full">
		<table class="w-full text-sm">
			<thead class="bg-gray-50 sticky top-0">
				<tr>
					<th class="px-3 py-2 text-left font-medium text-gray-600">{m.timestamp()}</th>
					<th class="px-3 py-2 text-right font-medium text-gray-600">{m.value()}</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-100">
				{#each [...chartData].reverse().slice(0, 20) as [timestamp, value]}
					<tr class="hover:bg-gray-50">
						<td class="px-3 py-2 text-gray-600">
							{new Date(timestamp).toLocaleString()}
						</td>
						<td class="px-3 py-2 text-right font-medium">
							{formatValue(value)}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		{#if chartData.length === 0}
			<div class="flex items-center justify-center h-32 text-gray-400">
				{m.noDataAvailable()}
			</div>
		{/if}
	</div>
{:else if samples.length > 0}
	<!-- ECharts -->
	<div id={chartId} class="w-full {height}"></div>
{:else}
	<!-- No data -->
	<div class="flex items-center justify-center h-full bg-gray-50 rounded-lg">
		<p class="text-gray-400 text-sm">{m.noDataAvailable()}</p>
	</div>
{/if}
