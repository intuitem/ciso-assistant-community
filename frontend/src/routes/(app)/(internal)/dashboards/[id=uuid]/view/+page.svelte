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
		Math.max(2, ...widgets.map((w: any) => (w.position_y || 0) + (w.height || 2)))
	);
</script>

<div class="p-6 space-y-4">
	<!-- Header -->
	<div class="flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboards/{dashboard.id}" class="btn preset-tonal">
				<i class="fa-solid fa-arrow-left"></i>
				{m.back()}
			</a>
			<h1 class="text-2xl font-bold">{dashboard.name}</h1>
			{#if dashboard.description}
				<span class="text-surface-500">- {dashboard.description}</span>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<a href="/dashboards/{dashboard.id}/layout" class="btn preset-tonal">
				<i class="fa-solid fa-grip"></i>
				{m.editLayout()}
			</a>
			<button class="btn preset-filled-primary-500" onclick={openAddWidgetModal}>
				<i class="fa-solid fa-plus"></i>
				{m.addWidget()}
			</button>
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
						<div class="mb-3">
							<h4 class="font-semibold text-base">
								{widget.display_title || widget.title || widget.metric_instance?.name}
							</h4>
							<p class="text-xs text-surface-500">
								{widget.chart_type_display} | {widget.time_range_display}
							</p>
						</div>

						<!-- Chart based on widget type -->
						<div class="flex-1 min-h-0">
							{#key widget.samples?.length}
								<DashboardWidgetChart {widget} samples={widget.samples || []} />
							{/key}
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="card p-12 bg-white dark:bg-surface-900 text-center">
				<i class="fa-solid fa-chart-line text-8xl text-surface-300 mb-6"></i>
				<p class="text-surface-500 text-lg mb-6">{m.noWidgetsYet()}</p>
				<button class="btn preset-filled-primary-500" onclick={openAddWidgetModal}>
					<i class="fa-solid fa-plus"></i>
					{m.addFirstWidget()}
				</button>
			</div>
		{/if}
	</div>
</div>
