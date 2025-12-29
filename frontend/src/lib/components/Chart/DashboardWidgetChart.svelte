<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import MarkdownRenderer from '../MarkdownRenderer.svelte';

	interface Props {
		widget: any;
		samples?: any[];
		builtinSamples?: any[]; // For builtin metrics
		height?: string;
	}

	let { widget, samples = [], builtinSamples = [], height = 'h-full' }: Props = $props();

	// Determine if this is a builtin metric widget
	const isBuiltinMetric = $derived(widget.is_builtin_metric || !!widget.target_content_type);

	const chartId = $derived(`widget-chart-${widget.id}`);
	const metricDefinition = $derived(widget.metric_instance?.metric_definition);
	const isQualitative = $derived(
		isBuiltinMetric ? false : metricDefinition?.category === 'qualitative'
	);

	// For builtin metrics, determine unit based on metric type
	const builtinMetricType = $derived(
		isBuiltinMetric ? getBuiltinMetricType(widget.metric_key) : null
	);

	// Check if this is a breakdown metric
	const isBreakdownMetric = $derived(builtinMetricType === 'breakdown');

	const unitName = $derived(
		isBuiltinMetric
			? builtinMetricType === 'percentage'
				? 'percentage'
				: ''
			: metricDefinition?.unit?.name || ''
	);
	// Units that should not be displayed (dimensionless or implicit)
	const HIDDEN_UNITS = ['score', 'count'];
	// Display symbol for unit (e.g., '%' instead of 'percentage', hide 'score'/'count')
	const unitSymbol = $derived(
		unitName === 'percentage' ? '%' : HIDDEN_UNITS.includes(unitName) ? '' : unitName
	);
	const targetValue = $derived(widget.metric_instance?.target_value);
	const higherIsBetter = $derived(metricDefinition?.higher_is_better ?? true);

	// Helper to determine builtin metric type
	function getBuiltinMetricType(metricKey: string): string {
		if (!metricKey) return 'number';
		if (metricKey === 'progress') return 'percentage';
		if (metricKey.endsWith('_breakdown')) return 'breakdown';
		return 'number';
	}

	// Color palette for breakdown charts (will be replaced with risk/compliance palette later)
	const BREAKDOWN_COLORS: string[] = [];

	// Format breakdown key for display (e.g., 'non_compliant' -> 'Non Compliant')
	function formatBreakdownKey(key: string): string {
		// Try to translate the key first
		const translated = safeTranslate(key);
		if (translated !== key) return translated;
		// Fall back to formatting the key
		return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}

	// Format value with unit
	function formatValueWithUnit(value: number | string): string {
		if (unitName === 'percentage') return `${value}%`;
		if (unitSymbol) return `${value} ${unitSymbol}`;
		return String(value);
	}

	// Prepare chart data from samples (custom metrics)
	const customChartData = $derived(
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

	// Prepare chart data from builtin metric samples
	const builtinChartData = $derived(
		builtinSamples
			.map((sample) => {
				const metricKey = widget.metric_key;
				const metrics = sample.metrics || {};
				const value = metrics[metricKey];
				// For breakdown metrics, we can't display as a single value chart
				// Instead, return the date and the full breakdown object
				if (builtinMetricType === 'breakdown') {
					return [sample.date, value ?? {}];
				}
				return [sample.date, value ?? null];
			})
			.filter((item) => item[1] !== null)
			.sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime())
	);

	// Combined chart data based on metric type
	const chartData = $derived(isBuiltinMetric ? builtinChartData : customChartData);

	// Get choice names for qualitative metrics
	const choiceNames = $derived(
		isQualitative ? metricDefinition?.choices_definition?.map((c: any) => c.name) || [] : []
	);

	// Get latest value for KPI/Gauge
	const latestValue = $derived(chartData.length > 0 ? chartData[chartData.length - 1][1] : null);

	// For breakdown metrics, get the latest breakdown data
	const latestBreakdown = $derived(
		isBreakdownMetric && chartData.length > 0 ? chartData[chartData.length - 1][1] : null
	);

	// Get all unique keys from breakdown data (for consistent legend/series)
	const breakdownKeys = $derived(() => {
		if (!isBreakdownMetric) return [];
		const keys = new Set<string>();
		for (const [, breakdown] of chartData) {
			if (breakdown && typeof breakdown === 'object') {
				Object.keys(breakdown).forEach((k) => keys.add(k));
			}
		}
		return Array.from(keys).sort();
	});

	// Prepare pie chart data from latest breakdown (uses ECharts default colors)
	const pieChartData = $derived(
		latestBreakdown && typeof latestBreakdown === 'object'
			? Object.entries(latestBreakdown).map(([key, value]) => ({
					name: formatBreakdownKey(key),
					value: value as number
				}))
			: []
	);

	// Prepare stacked bar/area data for breakdown time series (uses ECharts default colors)
	const breakdownTimeSeriesData = $derived(() => {
		if (!isBreakdownMetric) return { categories: [], series: [] };
		const keys = breakdownKeys();
		const categories = chartData.map(([date]) => new Date(date).toLocaleDateString());
		const series = keys.map((key) => ({
			name: formatBreakdownKey(key),
			type: widget.chart_type === 'area' ? 'line' : 'bar',
			stack: 'total',
			areaStyle: widget.chart_type === 'area' ? {} : undefined,
			data: chartData.map(([, breakdown]) =>
				breakdown && typeof breakdown === 'object' ? breakdown[key] || 0 : 0
			)
		}));
		return { categories, series };
	});

	let chartInstance: any = null;

	onMount(async () => {
		// Skip ECharts for text widgets - they render markdown, not charts
		if (widget.chart_type === 'text') {
			return;
		}
		// Skip ECharts for KPI/table with scalar values, but allow for breakdown metrics
		if ((widget.chart_type === 'kpi_card' || widget.chart_type === 'table') && !isBreakdownMetric) {
			return; // These don't use ECharts for scalar values
		}
		// For breakdown table, we don't need ECharts
		if (widget.chart_type === 'table' && isBreakdownMetric) {
			return;
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
			bottom: 60,
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
				} else if (!isQualitative && unitSymbol) {
					displayValue = formatValueWithUnit(value);
				}

				return `${date}<br/>${params[0].marker}${displayValue}`;
			}
		};

		const baseXAxis = {
			type: 'time',
			axisLabel: {
				formatter: function (value: number) {
					return new Date(value).toLocaleDateString();
				},
				rotate: 45
			}
		};

		const baseYAxis = {
			type: 'value',
			name: isQualitative ? '' : unitSymbol,
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

		// For breakdown metrics, render as stacked bar or pie
		if (isBreakdownMetric) {
			const tsData = breakdownTimeSeriesData();

			// For bar/area with breakdown, use stacked chart
			if (widget.chart_type === 'bar' || widget.chart_type === 'area') {
				return {
					grid: { ...baseGrid, right: 100 },
					tooltip: {
						trigger: 'axis',
						axisPointer: { type: 'shadow' }
					},
					legend: {
						show: widget.show_legend !== false,
						orient: 'vertical',
						right: 10,
						top: 'center',
						type: 'scroll'
					},
					xAxis: {
						type: 'category',
						data: tsData.categories,
						axisLabel: { rotate: 45 }
					},
					yAxis: { type: 'value', min: 0 },
					series: tsData.series
				};
			}

			// For pie chart with breakdown, use solid pie (no hole)
			if (widget.chart_type === 'pie') {
				return {
					tooltip: {
						trigger: 'item',
						formatter: '{b}: {c} ({d}%)'
					},
					legend: {
						show: widget.show_legend !== false,
						orient: 'vertical',
						right: 10,
						top: 'center',
						type: 'scroll'
					},
					series: [
						{
							type: 'pie',
							radius: '70%',
							center: ['40%', '50%'],
							avoidLabelOverlap: true,
							itemStyle: {
								borderRadius: 4,
								borderColor: '#fff',
								borderWidth: 2
							},
							label: {
								show: false
							},
							emphasis: {
								label: {
									show: true,
									fontSize: 14,
									fontWeight: 'bold'
								}
							},
							labelLine: { show: false },
							data: pieChartData
						}
					]
				};
			}

			// For donut/gauge/kpi_card with breakdown, use donut chart
			if (
				widget.chart_type === 'donut' ||
				widget.chart_type === 'gauge' ||
				widget.chart_type === 'kpi_card'
			) {
				return {
					tooltip: {
						trigger: 'item',
						formatter: '{b}: {c} ({d}%)'
					},
					legend: {
						show: widget.show_legend !== false,
						orient: 'vertical',
						right: 10,
						top: 'center',
						type: 'scroll'
					},
					series: [
						{
							type: 'pie',
							radius: ['40%', '70%'],
							center: ['40%', '50%'],
							avoidLabelOverlap: true,
							itemStyle: {
								borderRadius: 4,
								borderColor: '#fff',
								borderWidth: 2
							},
							label: {
								show: false
							},
							emphasis: {
								label: {
									show: true,
									fontSize: 14,
									fontWeight: 'bold'
								}
							},
							labelLine: { show: false },
							data: pieChartData
						}
					]
				};
			}
		}

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
				// For percentage metrics, always use 100 as max; otherwise use target or 100 as fallback
				const gaugeMax = unitName === 'percentage' ? 100 : (targetValue ?? 100);
				const gaugeValue = latestValue || 0;
				// Calculate target position on the gauge (as a ratio from 0 to 1)
				const targetRatio = widget.show_target && targetValue ? targetValue / gaugeMax : null;
				return {
					series: [
						{
							type: 'gauge',
							startAngle: 200,
							endAngle: -20,
							min: 0,
							max: gaugeMax,
							splitNumber: 5,
							center: ['50%', '60%'],
							radius: '90%',
							itemStyle: {
								color: 'rgb(59, 130, 246)'
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
									color:
										targetRatio !== null
											? [
													[targetRatio, 'rgba(200, 200, 200, 0.3)'],
													[targetRatio + 0.005, 'rgb(234, 88, 12)'], // Orange target marker
													[1, 'rgba(200, 200, 200, 0.3)']
												]
											: [[1, 'rgba(200, 200, 200, 0.3)']]
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
								formatter:
									unitName === 'percentage'
										? '{value}%'
										: unitSymbol
											? `{value} ${unitSymbol}`
											: '{value}',
								fontSize: 20,
								offsetCenter: [0, '40%']
							},
							data: [
								{
									value: gaugeValue,
									name:
										widget.show_target && targetValue
											? `${m.target()}: ${formatValueWithUnit(targetValue)}`
											: ''
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

			case 'donut':
				// For percentage metrics, show as actual vs remaining
				const donutValue = latestValue || 0;
				const maxValue = unitName === 'percentage' ? 100 : targetValue || 100;
				const remaining = Math.max(0, maxValue - donutValue);
				return {
					tooltip: {
						trigger: 'item',
						formatter: '{b}: {c} ({d}%)'
					},
					legend: {
						show: widget.show_legend !== false,
						orient: 'horizontal',
						bottom: 10
					},
					series: [
						{
							type: 'pie',
							radius: ['40%', '70%'],
							center: ['50%', '45%'],
							avoidLabelOverlap: true,
							itemStyle: {
								borderRadius: 4,
								borderColor: '#fff',
								borderWidth: 2
							},
							label: {
								show: false
							},
							emphasis: {
								label: {
									show: true,
									fontSize: 14,
									fontWeight: 'bold'
								}
							},
							labelLine: { show: false },
							data: [
								{ value: donutValue, name: m.actual(), itemStyle: { color: '#3b82f6' } },
								{ value: remaining, name: m.remaining(), itemStyle: { color: '#e5e7eb' } }
							]
						}
					]
				};

			default:
				return {};
		}
	}

	// Format display value (without unit, for separate styling)
	function formatValueOnly(value: any): string {
		if (value === null || value === undefined) return 'N/A';
		if (isQualitative && choiceNames[value - 1]) {
			return choiceNames[value - 1];
		}
		return String(value);
	}

	// Format display value with unit
	function formatValue(value: any): string {
		if (value === null || value === undefined) return 'N/A';
		if (isQualitative && choiceNames[value - 1]) {
			return choiceNames[value - 1];
		}
		return formatValueWithUnit(value);
	}
</script>

{#if widget.chart_type === 'text'}
	<!-- Text widget with markdown rendering -->
	<div class="h-full overflow-auto p-2">
		<MarkdownRenderer content={widget.text_content} />
	</div>
{:else if widget.chart_type === 'kpi_card' && !isBreakdownMetric}
	<!-- KPI Card for scalar values -->
	<div class="flex items-center justify-center h-full">
		<div class="flex items-baseline gap-3">
			<!-- Main value and unit -->
			<div class="flex items-baseline gap-1">
				<span class="text-4xl font-bold text-primary-600">{formatValueOnly(latestValue)}</span>
				{#if unitSymbol}
					<span class="text-2xl font-medium text-primary-500 lowercase"
						>{safeTranslate(unitSymbol)}</span
					>
				{/if}
			</div>
			<!-- Trend indicator -->
			{#if chartData.length > 1}
				{@const prevValue = chartData[chartData.length - 2]?.[1]}
				{@const change = prevValue
					? (((latestValue - prevValue) / prevValue) * 100).toFixed(1)
					: null}
				{@const isPositiveChange = Number(change) >= 0}
				{@const isGood = higherIsBetter ? isPositiveChange : !isPositiveChange}
				{#if change !== null}
					<div
						class="text-base font-medium px-2 py-0.5 rounded {isGood
							? 'text-green-700 bg-green-100'
							: 'text-red-700 bg-red-100'}"
					>
						{isPositiveChange ? '↑' : '↓'}
						{Math.abs(Number(change))}%
					</div>
				{/if}
			{/if}
		</div>
	</div>
	<!-- Target below, centered -->
	{#if widget.show_target && targetValue}
		<div class="text-sm text-surface-500 text-center -mt-2">
			{m.target()}: {formatValue(targetValue)}
		</div>
	{/if}
{:else if widget.chart_type === 'kpi_card' && isBreakdownMetric}
	<!-- KPI Card for breakdown - show as pie chart using ECharts -->
	{#if pieChartData.length > 0}
		<div id={chartId} class="w-full {height}"></div>
	{:else}
		<div class="flex items-center justify-center h-full bg-gray-50 rounded-lg">
			<p class="text-gray-400 text-sm">{m.noDataAvailable()}</p>
		</div>
	{/if}
{:else if widget.chart_type === 'table' && !isBreakdownMetric}
	<!-- Table for scalar values -->
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
{:else if widget.chart_type === 'table' && isBreakdownMetric}
	<!-- Table for breakdown - show latest breakdown as category/count table -->
	<div class="overflow-auto h-full">
		{#if latestBreakdown && typeof latestBreakdown === 'object'}
			<table class="w-full text-sm">
				<thead class="bg-gray-50 sticky top-0">
					<tr>
						<th class="px-3 py-2 text-left font-medium text-gray-600">{m.category()}</th>
						<th class="px-3 py-2 text-right font-medium text-gray-600">{m.count()}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-100">
					{#each Object.entries(latestBreakdown) as [key, count], index}
						<tr class="hover:bg-gray-50">
							<td class="px-3 py-2 text-gray-600 flex items-center gap-2">
								<span
									class="w-3 h-3 rounded-full"
									style="background-color: {BREAKDOWN_COLORS[index % BREAKDOWN_COLORS.length]}"
								></span>
								{formatBreakdownKey(key)}
							</td>
							<td class="px-3 py-2 text-right font-medium">
								{count}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<div class="flex items-center justify-center h-32 text-gray-400">
				{m.noDataAvailable()}
			</div>
		{/if}
	</div>
{:else if samples.length > 0 || builtinSamples.length > 0}
	<!-- ECharts -->
	<div id={chartId} class="w-full {height}"></div>
{:else}
	<!-- No data -->
	<div class="flex items-center justify-center h-full bg-gray-50 rounded-lg">
		<p class="text-gray-400 text-sm">{m.noDataAvailable()}</p>
	</div>
{/if}
