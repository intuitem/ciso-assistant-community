<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { m } from '$paraglide/messages';
	import { invalidate, goto } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';
	import { enhance } from '$app/forms';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const dashboard = $derived(data.data);
	const widgetModel = $derived(data.widgetModel);
	const widgetCreateForm = $derived(data.widgetCreateForm);

	let widgets = $state(data.widgets || []);
	let isDragging = $state(false);
	let draggedWidget = $state<any>(null);
	let isSaving = $state(false);
	let hasChanges = $state(false);

	const modalStore = getModalStore();
	const toastStore = getToastStore();

	// Grid configuration
	const GRID_COLS = 12;
	const ROW_HEIGHT = 150; // pixels per row unit

	// Watch for modal close and refresh data
	let previousModalCount = 0;
	onMount(() => {
		const unsubscribe = modalStore.subscribe((modals) => {
			if (previousModalCount > 0 && modals.length === 0) {
				refreshWidgets();
			}
			previousModalCount = modals.length;
		});

		return unsubscribe;
	});

	async function refreshWidgets() {
		await invalidate('dashboard:widgets');
		widgets = data.widgets || [];
	}

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

	function confirmDeleteWidget(widget: any) {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: ConfirmModal,
				props: {
					formAction: `/dashboard-widgets/${widget.id}?/delete`,
					invalidateAll: false
				}
			},
			title: m.confirmModalTitle(),
			body: `${m.confirmModalMessage()}: ${widget.display_title || widget.title || 'Widget'}?`
		});
	}

	// Drag and drop handlers
	function handleDragStart(event: DragEvent, widget: any) {
		isDragging = true;
		draggedWidget = widget;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.setData('text/plain', widget.id);
		}
	}

	function handleDragEnd() {
		isDragging = false;
		draggedWidget = null;
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleDrop(event: DragEvent, targetX: number, targetY: number) {
		event.preventDefault();
		if (!draggedWidget) return;

		// Update widget position
		const widgetIndex = widgets.findIndex((w: any) => w.id === draggedWidget.id);
		if (widgetIndex !== -1) {
			widgets[widgetIndex] = {
				...widgets[widgetIndex],
				position_x: Math.max(0, Math.min(targetX, GRID_COLS - (widgets[widgetIndex].width || 6))),
				position_y: Math.max(0, targetY)
			};
			hasChanges = true;
		}

		isDragging = false;
		draggedWidget = null;
	}

	// Resize handlers
	function handleResize(widget: any, newWidth: number, newHeight: number) {
		const widgetIndex = widgets.findIndex((w: any) => w.id === widget.id);
		if (widgetIndex !== -1) {
			widgets[widgetIndex] = {
				...widgets[widgetIndex],
				width: Math.max(1, Math.min(newWidth, GRID_COLS - widget.position_x)),
				height: Math.max(1, newHeight)
			};
			hasChanges = true;
		}
	}

	// Get widgets JSON for form submission
	const widgetsJson = $derived(JSON.stringify(widgets.map((w: any) => ({
		id: w.id,
		position_x: w.position_x,
		position_y: w.position_y,
		width: w.width,
		height: w.height
	}))));

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
			4,
			...widgets.map((w: any) => (w.position_y || 0) + (w.height || 2))
		)
	);
</script>

<div class="p-4 space-y-4">
	<!-- Header -->
	<div class="flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboards/{dashboard.id}" class="btn preset-tonal">
				<iconify-icon icon="mdi:arrow-left" class="text-xl"></iconify-icon>
				{m.back()}
			</a>
			<h1 class="text-2xl font-bold">{m.edit()}: {dashboard.name}</h1>
		</div>
		<div class="flex items-center gap-2">
			<button class="btn preset-filled-primary-500" onclick={openAddWidgetModal}>
				<iconify-icon icon="mdi:plus" class="text-xl"></iconify-icon>
				{m.addWidget()}
			</button>
			{#if hasChanges}
				<form
					method="POST"
					action="?/saveLayout"
					use:enhance={() => {
						isSaving = true;
						return async ({ result }) => {
							isSaving = false;
							if (result.type === 'success') {
								hasChanges = false;
								toastStore.trigger({
									message: m.layoutSaved(),
									background: 'preset-filled-success-500'
								});
							} else {
								toastStore.trigger({
									message: m.anErrorOccurred(),
									background: 'preset-filled-error-500'
								});
							}
						};
					}}
					class="inline"
				>
					<input type="hidden" name="widgets" value={widgetsJson} />
					<button
						type="submit"
						class="btn preset-filled-success-500"
						disabled={isSaving}
					>
						{#if isSaving}
							<iconify-icon icon="mdi:loading" class="text-xl animate-spin"></iconify-icon>
						{:else}
							<iconify-icon icon="mdi:content-save" class="text-xl"></iconify-icon>
						{/if}
						{m.save()}
					</button>
				</form>
			{/if}
		</div>
	</div>

	<!-- Instructions -->
	<div class="card p-3 bg-blue-50 text-blue-800 text-sm">
		<iconify-icon icon="mdi:information" class="text-lg mr-2"></iconify-icon>
		{m.dashboardEditorInstructions()}
	</div>

	<!-- Grid Editor -->
	<div class="relative bg-gray-100 rounded-lg p-4 min-h-[600px]">
		<!-- Grid background -->
		<div
			class="absolute inset-4 grid gap-2 pointer-events-none opacity-20"
			style="grid-template-columns: repeat({GRID_COLS}, 1fr); grid-template-rows: repeat({maxRow}, {ROW_HEIGHT}px);"
		>
			{#each Array(GRID_COLS * maxRow) as _, i}
				<div class="border border-dashed border-gray-400 rounded"></div>
			{/each}
		</div>

		<!-- Widgets Grid -->
		{#if widgets.length > 0}
			<div
				class="relative grid gap-2"
				style="grid-template-columns: repeat({GRID_COLS}, 1fr); grid-template-rows: repeat({maxRow}, {ROW_HEIGHT}px);"
				ondragover={handleDragOver}
				ondrop={(e) => {
					const rect = e.currentTarget.getBoundingClientRect();
					const cellWidth = rect.width / GRID_COLS;
					const targetX = Math.floor((e.clientX - rect.left) / cellWidth);
					const targetY = Math.floor((e.clientY - rect.top) / ROW_HEIGHT);
					handleDrop(e, targetX, targetY);
				}}
				role="grid"
			>
				{#each widgets as widget (widget.id)}
					<div
						class="card bg-white shadow-md p-3 cursor-move relative group transition-shadow hover:shadow-lg {isDragging && draggedWidget?.id === widget.id ? 'opacity-50' : ''}"
						style={getWidgetStyle(widget)}
						draggable="true"
						ondragstart={(e) => handleDragStart(e, widget)}
						ondragend={handleDragEnd}
						role="gridcell"
					>
						<!-- Widget Header -->
						<div class="flex justify-between items-start mb-2">
							<div class="flex-1 min-w-0">
								<h4 class="font-semibold text-sm truncate">
									{widget.display_title || widget.title || widget.metric_instance?.name || 'Widget'}
								</h4>
								<p class="text-xs text-gray-500 truncate">
									{widget.chart_type_display || widget.chart_type}
								</p>
							</div>
							<div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
								<a
									href="/dashboard-widgets/{widget.id}/edit"
									class="btn btn-sm preset-tonal p-1"
									title={m.edit()}
								>
									<iconify-icon icon="mdi:pencil" class="text-sm"></iconify-icon>
								</a>
								<button
									class="btn btn-sm preset-filled-error-500 p-1"
									onclick={() => confirmDeleteWidget(widget)}
									title={m.delete()}
								>
									<iconify-icon icon="mdi:delete" class="text-sm"></iconify-icon>
								</button>
							</div>
						</div>

						<!-- Widget Preview -->
						<div class="flex-1 bg-gray-50 rounded flex items-center justify-center text-gray-400 min-h-[60px]">
							<iconify-icon
								icon={widget.chart_type === 'kpi_card' ? 'mdi:card-text' :
									  widget.chart_type === 'bar' ? 'mdi:chart-bar' :
									  widget.chart_type === 'gauge' ? 'mdi:gauge' :
									  widget.chart_type === 'sparkline' ? 'mdi:chart-timeline-variant' :
									  widget.chart_type === 'table' ? 'mdi:table' :
									  widget.chart_type === 'area' ? 'mdi:chart-areaspline' :
									  'mdi:chart-line'}
								class="text-4xl"
							></iconify-icon>
						</div>

						<!-- Position info -->
						<div class="absolute bottom-1 left-1 text-xs text-gray-400 opacity-0 group-hover:opacity-100">
							{widget.position_x},{widget.position_y} ({widget.width}x{widget.height})
						</div>

						<!-- Resize handle -->
						<div
							class="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize opacity-0 group-hover:opacity-100 bg-gray-300 rounded-tl"
							onmousedown={(e) => {
								e.preventDefault();
								const startX = e.clientX;
								const startY = e.clientY;
								const startWidth = widget.width || 6;
								const startHeight = widget.height || 2;
								// Capture grid width at start of resize
								const gridElement = (e.currentTarget as HTMLElement).closest('.grid');
								const gridWidth = gridElement?.clientWidth || 800;
								const colWidth = gridWidth / GRID_COLS;

								const onMouseMove = (moveEvent: MouseEvent) => {
									const deltaX = moveEvent.clientX - startX;
									const deltaY = moveEvent.clientY - startY;

									const newWidth = Math.round(startWidth + deltaX / colWidth);
									const newHeight = Math.round(startHeight + deltaY / ROW_HEIGHT);

									handleResize(widget, newWidth, newHeight);
								};

								const onMouseUp = () => {
									document.removeEventListener('mousemove', onMouseMove);
									document.removeEventListener('mouseup', onMouseUp);
								};

								document.addEventListener('mousemove', onMouseMove);
								document.addEventListener('mouseup', onMouseUp);
							}}
							role="slider"
							aria-label="Resize widget"
							tabindex="0"
						></div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="flex flex-col items-center justify-center h-[400px] text-gray-500">
				<iconify-icon icon="mdi:view-dashboard-outline" class="text-6xl mb-4"></iconify-icon>
				<p class="mb-4">{m.noWidgetsYet()}</p>
				<button class="btn preset-filled-primary-500" onclick={openAddWidgetModal}>
					<iconify-icon icon="mdi:plus" class="text-xl"></iconify-icon>
					{m.addFirstWidget()}
				</button>
			</div>
		{/if}
	</div>
</div>
