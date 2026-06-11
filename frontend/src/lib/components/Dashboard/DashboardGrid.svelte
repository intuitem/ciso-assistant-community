<script lang="ts">
	import DashboardWidgetChart from '$lib/components/Chart/DashboardWidgetChart.svelte';

	interface Props {
		widgets: any[];
	}

	let { widgets }: Props = $props();

	const GRID_COLS = 12;
	const ROW_HEIGHT = 150;

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

	function getEffectiveChartTypeDisplay(widget: any): string {
		const isBreakdownMetric = widget.metric_key && widget.metric_key.endsWith('_breakdown');

		if (isBreakdownMetric) {
			if (
				widget.chart_type === 'donut' ||
				widget.chart_type === 'pie' ||
				widget.chart_type === 'bar' ||
				widget.chart_type === 'table'
			) {
				return widget.chart_type_display;
			}
			return chartTypeLabels['donut'] || 'Donut';
		}

		return widget.chart_type_display;
	}

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

	const maxRow = $derived(
		Math.max(2, ...widgets.map((w: any) => (w.position_y || 0) + (w.height || 2)))
	);
</script>

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
{/if}
