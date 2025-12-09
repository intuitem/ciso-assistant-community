<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import MetricSampleChart from '$lib/components/Chart/MetricSampleChart.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import { invalidate } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	const dashboard = $derived(data.data);
	const dashboardWidgets = $derived(data.widgets || []);
	const widgetModel = $derived(data.widgetModel);
	const widgetCreateForm = $derived(data.widgetCreateForm);

	const modalStore = getModalStore();

	// Watch for modal close and refresh data
	let previousModalCount = 0;
	onMount(() => {
		const unsubscribe = modalStore.subscribe((modals) => {
			if (previousModalCount > 0 && modals.length === 0) {
				invalidate('dashboard:widgets');
			}
			previousModalCount = modals.length;
		});

		return unsubscribe;
	});

	function openAddWidgetModal() {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: CreateModal,
				props: {
					form: widgetCreateForm,
					model: widgetModel,
					formAction: '/dashboard-widgets?/create'
				}
			},
			title: safeTranslate('addWidget')
		});
	}

	// Get chart type icon
	function getChartIcon(chartType: string): string {
		const icons: Record<string, string> = {
			line: 'mdi:chart-line',
			bar: 'mdi:chart-bar',
			area: 'mdi:chart-areaspline',
			gauge: 'mdi:gauge',
			kpi_card: 'mdi:card-text',
			sparkline: 'mdi:chart-timeline-variant',
			table: 'mdi:table'
		};
		return icons[chartType] || 'mdi:chart-line';
	}
</script>

<DetailView {data} {form}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<!-- Dashboard Header -->
			<div class="flex justify-between items-center">
				<h3 class="text-lg font-semibold">{m.widgets()} ({dashboardWidgets.length})</h3>
				<button class="btn preset-filled-primary-500 btn-sm" onclick={openAddWidgetModal}>
					<iconify-icon icon="mdi:plus" class="text-xl"></iconify-icon>
					{m.addWidget()}
				</button>
			</div>

			<!-- Widgets Grid -->
			{#if dashboardWidgets.length > 0}
				<div class="grid grid-cols-12 gap-4 auto-rows-min">
					{#each dashboardWidgets as widget (widget.id)}
						{@const widgetWidth = widget.width || 6}
						{@const widgetHeight = widget.height || 2}
						{@const gridCol = `grid-column: span ${Math.min(widgetWidth, 12)} / span ${Math.min(widgetWidth, 12)}`}
						{@const minHeight = `min-height: ${widgetHeight * 150}px`}
						<div class="card p-4 bg-white shadow-sm" style="{gridCol}; {minHeight}">
							<div class="flex justify-between items-start mb-3">
								<div>
									<h4 class="font-semibold text-base">
										{widget.display_title || widget.title || widget.metric_instance?.name}
									</h4>
									<p class="text-xs text-gray-500">
										{widget.chart_type_display} | {widget.time_range_display}
									</p>
								</div>
								<div class="flex gap-1">
									<a
										href="/dashboard-widgets/{widget.id}/edit"
										class="btn btn-sm preset-tonal"
										title={m.edit()}
									>
										<iconify-icon icon="mdi:pencil" class="text-sm"></iconify-icon>
									</a>
								</div>
							</div>

							<!-- Chart based on widget type -->
							{#if widget.chart_type === 'kpi_card'}
								<div class="flex items-center justify-center h-full">
									<div class="text-center">
										<div class="text-4xl font-bold text-primary-600">
											{widget.samples?.[0]?.display_value || 'N/A'}
										</div>
										{#if widget.show_target && widget.metric_instance?.target_value}
											<div class="text-sm text-gray-500 mt-2">
												{m.target()}: {widget.metric_instance.target_value}
											</div>
										{/if}
									</div>
								</div>
							{:else}
								{#key widget.samples?.length}
									<MetricSampleChart
										samples={widget.samples || []}
										metricDefinition={widget.metric_instance?.metric_definition}
										height="h-48"
									/>
								{/key}
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<div class="card p-8 bg-gray-50 text-center">
					<iconify-icon icon="mdi:view-dashboard-outline" class="text-6xl text-gray-300 mb-4"
					></iconify-icon>
					<p class="text-gray-500 mb-4">{m.noWidgetsYet()}</p>
					<button class="btn preset-filled-primary-500" onclick={openAddWidgetModal}>
						<iconify-icon icon="mdi:plus" class="text-xl"></iconify-icon>
						{m.addFirstWidget()}
					</button>
				</div>
			{/if}
		</div>
	{/snippet}
</DetailView>
