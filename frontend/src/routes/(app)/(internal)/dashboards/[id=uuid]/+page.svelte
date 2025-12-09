<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	const dashboard = $derived(data.data);
	const dashboardWidgets = $derived(data.widgets || []);
</script>

<DetailView {data} {form}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<!-- Dashboard Actions -->
			<div class="flex flex-col gap-4">
				<div class="flex justify-between items-center">
					<h3 class="text-lg font-semibold">{m.widgets()} ({dashboardWidgets.length})</h3>
				</div>

				<!-- Action buttons -->
				<div class="flex flex-wrap gap-2">
					<a href="/dashboards/{dashboard.id}/view" class="btn preset-filled-primary-500">
						<i class="fa-solid fa-chart-line"></i>
						{m.viewDashboard()}
					</a>
					<a href="/dashboards/{dashboard.id}/edit" class="btn preset-tonal">
						<i class="fa-solid fa-pencil"></i>
						{m.editLayout()}
					</a>
				</div>

				<!-- Widget list preview -->
				{#if dashboardWidgets.length > 0}
					<div class="space-y-2">
						{#each dashboardWidgets as widget (widget.id)}
							<div class="card p-3 bg-white shadow-sm flex items-center justify-between">
								<div class="flex items-center gap-3">
									<i class="text-2xl text-gray-400 fa-solid {widget.chart_type === 'kpi_card' ? 'fa-square-poll-vertical' :
											  widget.chart_type === 'bar' ? 'fa-chart-bar' :
											  widget.chart_type === 'gauge' ? 'fa-gauge-high' :
											  widget.chart_type === 'sparkline' ? 'fa-chart-area' :
											  widget.chart_type === 'table' ? 'fa-table' :
											  widget.chart_type === 'area' ? 'fa-chart-area' :
											  'fa-chart-line'}"></i>
									<div>
										<p class="font-medium text-sm">
											{widget.display_title || widget.title || widget.metric_instance?.name}
										</p>
										<p class="text-xs text-gray-500">
											{widget.chart_type_display} | {widget.time_range_display}
										</p>
									</div>
								</div>
								<a
									href="/dashboard-widgets/{widget.id}/edit"
									class="btn btn-sm preset-tonal"
									title={m.edit()}
								>
									<i class="fa-solid fa-pencil text-sm"></i>
								</a>
							</div>
						{/each}
					</div>
				{:else}
					<div class="card p-6 bg-gray-50 text-center">
						<i class="fa-solid fa-chart-line text-4xl text-gray-300 mb-2"></i>
						<p class="text-gray-500 text-sm">{m.noWidgetsYet()}</p>
					</div>
				{/if}
			</div>
		</div>
	{/snippet}
</DetailView>
