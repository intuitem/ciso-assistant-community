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
						<iconify-icon icon="mdi:view-dashboard" class="text-xl"></iconify-icon>
						{m.viewDashboard()}
					</a>
					<a href="/dashboards/{dashboard.id}/edit" class="btn preset-tonal">
						<iconify-icon icon="mdi:pencil" class="text-xl"></iconify-icon>
						{m.editLayout()}
					</a>
				</div>

				<!-- Widget list preview -->
				{#if dashboardWidgets.length > 0}
					<div class="space-y-2">
						{#each dashboardWidgets as widget (widget.id)}
							<div class="card p-3 bg-white shadow-sm flex items-center justify-between">
								<div class="flex items-center gap-3">
									<iconify-icon
										icon={widget.chart_type === 'kpi_card' ? 'mdi:card-text' :
											  widget.chart_type === 'bar' ? 'mdi:chart-bar' :
											  widget.chart_type === 'gauge' ? 'mdi:gauge' :
											  widget.chart_type === 'sparkline' ? 'mdi:chart-timeline-variant' :
											  widget.chart_type === 'table' ? 'mdi:table' :
											  widget.chart_type === 'area' ? 'mdi:chart-areaspline' :
											  'mdi:chart-line'}
										class="text-2xl text-gray-400"
									></iconify-icon>
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
									<iconify-icon icon="mdi:pencil" class="text-sm"></iconify-icon>
								</a>
							</div>
						{/each}
					</div>
				{:else}
					<div class="card p-6 bg-gray-50 text-center">
						<iconify-icon icon="mdi:view-dashboard-outline" class="text-4xl text-gray-300 mb-2"></iconify-icon>
						<p class="text-gray-500 text-sm">{m.noWidgetsYet()}</p>
					</div>
				{/if}
			</div>
		</div>
	{/snippet}
</DetailView>
