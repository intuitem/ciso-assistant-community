<script lang="ts">
	import type { PageData } from './$types';
	import DashboardWidgetChart from '$lib/components/Chart/DashboardWidgetChart.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const dashboard = $derived(data.data);
	const widgets = $derived(data.widgets || []);

	// Grid configuration
	const GRID_COLS = 12;
	const ROW_HEIGHT = 150;

	// Chart type labels
	const chartTypeLabels: Record<string, string> = {
		kpi_card: 'KPI Card',
		gauge: 'Gauge',
		sparkline: 'Sparkline',
		line: 'Line',
		area: 'Area',
		bar: 'Bar',
		table: 'Table',
		donut: 'Donut',
		pie: 'Pie',
		text: 'Text'
	};

	// Get effective chart type display (accounting for breakdown fallbacks)
	function getEffectiveChartTypeDisplay(widget: any): string {
		// Check if this is a breakdown metric
		const isBreakdownMetric = widget.metric_key && widget.metric_key.endsWith('_breakdown');

		if (isBreakdownMetric) {
			// For breakdown metrics, donut, pie, bar and table are valid
			if (
				widget.chart_type === 'donut' ||
				widget.chart_type === 'pie' ||
				widget.chart_type === 'bar' ||
				widget.chart_type === 'table'
			) {
				return widget.chart_type_display;
			}
			// Other types (kpi_card, gauge) fall back to donut for breakdowns
			return chartTypeLabels['donut'] || 'Donut';
		}

		return widget.chart_type_display;
	}

	// Calculate grid position style
	function getWidgetStyle(widget: any): string {
		const x = widget.position_x || 0;
		const y = widget.position_y || 0;
		const w = widget.width || 6;
		const h = widget.height || 2;

		return `
			grid-column: ${x + 1} / span ${w};
			grid-row: ${y + 1} / span ${h};
			min-height: ${h * ROW_HEIGHT}px;
		`;
	}

	// Get max row for grid sizing
	const maxRow = $derived(
		Math.max(2, ...widgets.map((w: any) => (w.position_y || 0) + (w.height || 2)))
	);
</script>

<div class="p-6 space-y-4">
	<!-- Header -->
	<div class="flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboards" class="btn preset-tonal">
				<i class="fa-solid fa-arrow-left"></i>
				{m.back()}
			</a>
			<h1 class="text-2xl font-bold">{dashboard.name}</h1>
			{#if dashboard.description}
				<span class="text-surface-500">- {dashboard.description}</span>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<a
				href="/dashboards/{dashboard.id}/edit?next=/dashboards/{dashboard.id}"
				class="btn preset-tonal"
			>
				<i class="fa-solid fa-pencil"></i>
				{m.editAttributes()}
			</a>
			<a href="/dashboards/{dashboard.id}/layout" class="btn preset-filled-primary-500">
				<i class="fa-solid fa-grip"></i>
				{m.editLayout()}
			</a>
		</div>
	</div>

	<!-- Widgets Grid - Full Width -->
	<div class="bg-surface-50-950 rounded-lg p-4 -mx-2">
		{#if widgets.length > 0}
			<div
				class="grid gap-4"
				style="grid-template-columns: repeat({GRID_COLS}, 1fr); grid-template-rows: repeat({maxRow}, {ROW_HEIGHT}px);"
			>
				{#each widgets as widget (widget.id)}
					<div
						class="card p-4 bg-white dark:bg-surface-900 shadow-sm flex flex-col"
						style={getWidgetStyle(widget)}
					>
						{#if widget.display_title || widget.title}
							<div class="mb-3">
								<h4 class="font-semibold text-base">
									{widget.display_title || widget.title}
								</h4>
								{#if widget.chart_type !== 'text'}
									<p class="text-xs text-surface-500">
										{getEffectiveChartTypeDisplay(widget)} | {widget.time_range_display}
									</p>
								{/if}
							</div>
						{/if}

						<!-- Chart based on widget type -->
						<div class="flex-1 min-h-0">
							{#key widget.samples?.length || widget.builtinSamples?.length}
								<DashboardWidgetChart
									{widget}
									samples={widget.samples || []}
									builtinSamples={widget.builtinSamples || []}
								/>
							{/key}
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="card p-12 bg-white dark:bg-surface-900 text-center">
				<i class="fa-solid fa-chart-line text-8xl text-surface-300 mb-6"></i>
				<p class="text-surface-500 text-lg mb-6">{m.noWidgetsYet()}</p>
				<a href="/dashboards/{dashboard.id}/layout" class="btn preset-filled-primary-500">
					<i class="fa-solid fa-pen-to-square"></i>
					{m.editLayout()}
				</a>
			</div>
		{/if}
	</div>
</div>
