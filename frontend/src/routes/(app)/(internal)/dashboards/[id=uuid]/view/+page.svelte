<script lang="ts">
	import type { PageData } from './$types';
	import DashboardWidgetChart from '$lib/components/Chart/DashboardWidgetChart.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { m } from '$paraglide/messages';
	import { invalidate } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const dashboard = $derived(data.data);
	const widgets = $derived(data.widgets || []);
	const widgetModel = $derived(data.widgetModel);
	const widgetCreateForm = $derived(data.widgetCreateForm);

	const modalStore = getModalStore();

	// Grid configuration
	const GRID_COLS = 12;
	const ROW_HEIGHT = 150;

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
		Math.max(
			2,
			...widgets.map((w: any) => (w.position_y || 0) + (w.height || 2))
		)
	);
</script>

<div class="p-6 space-y-4">
	<!-- Header -->
	<div class="flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboards/{dashboard.id}" class="btn preset-tonal">
				<iconify-icon icon="mdi:arrow-left" class="text-xl"></iconify-icon>
				{m.back()}
			</a>
			<h1 class="text-2xl font-bold">{dashboard.name}</h1>
			{#if dashboard.description}
				<span class="text-gray-500">- {dashboard.description}</span>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<a href="/dashboards/{dashboard.id}/edit" class="btn preset-tonal">
				<iconify-icon icon="mdi:pencil" class="text-xl"></iconify-icon>
				{m.editLayout()}
			</a>
			<button class="btn preset-filled-primary-500" onclick={openAddWidgetModal}>
				<iconify-icon icon="mdi:plus" class="text-xl"></iconify-icon>
				{m.addWidget()}
			</button>
		</div>
	</div>

	<!-- Widgets Grid - Full Width -->
	{#if widgets.length > 0}
		<div
			class="grid gap-4"
			style="grid-template-columns: repeat({GRID_COLS}, 1fr); grid-template-rows: repeat({maxRow}, {ROW_HEIGHT}px);"
		>
			{#each widgets as widget (widget.id)}
				<div
					class="card p-4 bg-white shadow-sm flex flex-col"
					style={getWidgetStyle(widget)}
				>
					<div class="flex justify-between items-start mb-3">
						<div>
							<h4 class="font-semibold text-base">
								{widget.display_title || widget.title || widget.metric_instance?.name}
							</h4>
							<p class="text-xs text-gray-500">
								{widget.chart_type_display} | {widget.time_range_display}
							</p>
						</div>
						<a
							href="/dashboard-widgets/{widget.id}/edit"
							class="btn btn-sm preset-tonal opacity-50 hover:opacity-100"
							title={m.edit()}
						>
							<iconify-icon icon="mdi:pencil" class="text-sm"></iconify-icon>
						</a>
					</div>

					<!-- Chart based on widget type -->
					<div class="flex-1 min-h-0">
						{#key widget.samples?.length}
							<DashboardWidgetChart
								{widget}
								samples={widget.samples || []}
							/>
						{/key}
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="card p-12 bg-gray-50 text-center">
			<iconify-icon icon="mdi:view-dashboard-outline" class="text-8xl text-gray-300 mb-6"></iconify-icon>
			<p class="text-gray-500 text-lg mb-6">{m.noWidgetsYet()}</p>
			<button class="btn preset-filled-primary-500" onclick={openAddWidgetModal}>
				<iconify-icon icon="mdi:plus" class="text-xl"></iconify-icon>
				{m.addFirstWidget()}
			</button>
		</div>
	{/if}
</div>
