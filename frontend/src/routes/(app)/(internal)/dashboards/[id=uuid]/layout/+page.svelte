<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
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
	const textWidgetModel = $derived(data.textWidgetModel);
	const textWidgetCreateForm = $derived(data.textWidgetCreateForm);
	const builtinWidgetModel = $derived(data.builtinWidgetModel);
	const builtinWidgetCreateForm = $derived(data.builtinWidgetCreateForm);
	const supportedModels = $derived(data.supportedModels || {});

	let widgets = $state(data.widgets || []);
	let isDragging = $state(false);
	let draggedWidget = $state<any>(null);
	let isSaving = $state(false);
	let hasChanges = $state(false);
	let gridElement: HTMLDivElement | null = $state(null);
	let extraRows = $state(0);

	const modalStore = getModalStore();
	const toastStore = getToastStore();

	// Grid configuration
	const GRID_COLS = 12;
	const ROW_HEIGHT = 150; // pixels per row unit
	const GRID_GAP = 8; // gap between cells in pixels

	// Minimum dimensions per chart type (width, height in grid units)
	const MIN_DIMENSIONS: Record<string, { width: number; height: number }> = {
		kpi_card: { width: 2, height: 1 },
		sparkline: { width: 3, height: 1 },
		gauge: { width: 3, height: 2 },
		donut: { width: 3, height: 2 },
		pie: { width: 3, height: 2 },
		line: { width: 4, height: 2 },
		bar: { width: 4, height: 2 },
		area: { width: 4, height: 2 },
		table: { width: 4, height: 2 },
		text: { width: 2, height: 1 }
	};

	// Chart type labels for display
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
				return widget.chart_type_display || chartTypeLabels[widget.chart_type] || widget.chart_type;
			}
			// Other types (kpi_card, gauge) fall back to donut for breakdowns
			return chartTypeLabels['donut'] || 'Donut';
		}

		return widget.chart_type_display || chartTypeLabels[widget.chart_type] || widget.chart_type;
	}

	// Get minimum dimensions for a widget based on its chart type
	function getMinDimensions(chartType: string): { width: number; height: number } {
		return MIN_DIMENSIONS[chartType] || { width: 2, height: 1 };
	}

	// Get accurate grid cell dimensions
	function getGridDimensions() {
		if (!gridElement) return { colWidth: 80, rowHeight: ROW_HEIGHT };
		const gridWidth = gridElement.clientWidth;
		const colWidth = (gridWidth - (GRID_COLS - 1) * GRID_GAP) / GRID_COLS;
		return { colWidth, rowHeight: ROW_HEIGHT };
	}

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

	function openAddCustomWidgetModal() {
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
			title: safeTranslate('addCustomWidget')
		});
	}

	function openAddBuiltinWidgetModal() {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: CreateModal,
				props: {
					form: builtinWidgetCreateForm,
					model: builtinWidgetModel,
					formAction: '/dashboard-builtin-widgets?/create',
					supportedModels: supportedModels
				}
			},
			title: safeTranslate('addBuiltinWidget')
		});
	}

	function openAddTextWidgetModal() {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: CreateModal,
				props: {
					form: textWidgetCreateForm,
					model: textWidgetModel,
					formAction: '/dashboard-widgets?/create'
				}
			},
			title: safeTranslate('addTextWidget')
		});
	}

	function confirmDeleteWidget(widget: any) {
		modalStore.trigger({
			type: 'component',
			component: {
				ref: DeleteConfirmModal,
				props: {
					_form: {},
					formAction: '?/delete',
					URLModel: 'dashboard-widgets',
					id: widget.id,
					invalidateAll: false
				}
			},
			title: m.deleteModalTitle(),
			body: m.deleteModalMessage({ name: widget.display_title || widget.title || 'Widget' })
		});
	}

	// Convert pixel position to grid coordinates
	function pixelToGrid(pixelX: number, pixelY: number): { gridX: number; gridY: number } {
		const { colWidth } = getGridDimensions();
		const cellWithGap = colWidth + GRID_GAP;
		const gridX = Math.round(pixelX / cellWithGap);
		const gridY = Math.round(pixelY / (ROW_HEIGHT + GRID_GAP));
		return { gridX, gridY };
	}

	// Drag and drop handlers
	let dragOffset = { x: 0, y: 0 };

	function handleDragStart(event: DragEvent, widget: any) {
		isDragging = true;
		draggedWidget = widget;

		// Calculate offset from widget top-left to mouse position
		const target = event.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		dragOffset = {
			x: event.clientX - rect.left,
			y: event.clientY - rect.top
		};

		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.setData('text/plain', widget.id);
			// Set drag image offset for better visual feedback
			event.dataTransfer.setDragImage(target, dragOffset.x, dragOffset.y);
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

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		if (!draggedWidget || !gridElement) return;

		const gridRect = gridElement.getBoundingClientRect();
		// Calculate position accounting for drag offset
		const relativeX = event.clientX - gridRect.left - dragOffset.x;
		const relativeY = event.clientY - gridRect.top - dragOffset.y;

		const { gridX, gridY } = pixelToGrid(relativeX, relativeY);

		// Update widget position with bounds checking
		const widgetIndex = widgets.findIndex((w: any) => w.id === draggedWidget.id);
		if (widgetIndex !== -1) {
			const widgetWidth = widgets[widgetIndex].width || 6;
			widgets[widgetIndex] = {
				...widgets[widgetIndex],
				position_x: Math.max(0, Math.min(gridX, GRID_COLS - widgetWidth)),
				position_y: Math.max(0, gridY)
			};
			hasChanges = true;
		}

		isDragging = false;
		draggedWidget = null;
	}

	// Resize handlers
	function updateWidgetSize(widgetId: string, newWidth: number, newHeight: number) {
		const widgetIndex = widgets.findIndex((w: any) => w.id === widgetId);
		if (widgetIndex !== -1) {
			const widget = widgets[widgetIndex];
			const maxWidth = GRID_COLS - (widget.position_x || 0);
			const minDims = getMinDimensions(widget.chart_type);
			widgets[widgetIndex] = {
				...widget,
				width: Math.max(minDims.width, Math.min(Math.round(newWidth), maxWidth)),
				height: Math.max(minDims.height, Math.round(newHeight))
			};
			hasChanges = true;
		}
	}

	// Get widgets JSON for form submission
	const widgetsJson = $derived(
		JSON.stringify(
			widgets.map((w: any) => ({
				id: w.id,
				position_x: w.position_x,
				position_y: w.position_y,
				width: w.width,
				height: w.height
			}))
		)
	);

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

	// Minimum rows required by widgets
	const minRequiredRows = $derived(
		Math.max(4, ...widgets.map((w: any) => (w.position_y || 0) + (w.height || 2)))
	);

	// Get max row for grid sizing (minimum required, plus any extra rows added by user)
	const maxRow = $derived(minRequiredRows + extraRows);

	// Can remove a row if there are extra rows beyond what widgets need
	const canRemoveRow = $derived(extraRows > 0);

	function addRow() {
		extraRows += 1;
	}

	function removeRow() {
		if (extraRows > 0) {
			extraRows -= 1;
		}
	}
</script>

<div class="p-4 space-y-4">
	<!-- Header -->
	<div class="flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboards/{dashboard.id}" class="btn preset-tonal">
				<i class="fa-solid fa-arrow-left"></i>
				{m.back()}
			</a>
			<h1 class="text-2xl font-bold">{m.edit()}: {dashboard.name}</h1>
		</div>
		<div class="flex items-center gap-2">
			<button
				class="btn bg-indigo-500 hover:bg-indigo-600 text-white"
				onclick={openAddBuiltinWidgetModal}
			>
				<i class="fa-solid fa-chart-simple"></i>
				{m.addBuiltinWidget()}
			</button>
			<button
				class="btn bg-violet-500 hover:bg-violet-600 text-white"
				onclick={openAddCustomWidgetModal}
			>
				<i class="fa-solid fa-sliders"></i>
				{m.addCustomWidget()}
			</button>
			<button class="btn bg-teal-500 hover:bg-teal-600 text-white" onclick={openAddTextWidgetModal}>
				<i class="fa-solid fa-font"></i>
				{m.addTextWidget()}
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
					<button type="submit" class="btn preset-filled-success-500" disabled={isSaving}>
						{#if isSaving}
							<i class="fa-solid fa-spinner fa-spin"></i>
						{:else}
							<i class="fa-solid fa-save"></i>
						{/if}
						{m.save()}
					</button>
				</form>
			{/if}
		</div>
	</div>

	<!-- Instructions -->
	<div class="card p-3 preset-tonal-primary text-sm">
		<i class="fa-solid fa-circle-info mr-2"></i>
		{m.dashboardEditorInstructions()}
	</div>

	<!-- Grid Editor -->
	<div class="bg-surface-50-950 rounded-lg p-4">
		{#if widgets.length > 0}
			<!-- Grid container with background -->
			<div class="relative">
				<!-- Grid background -->
				<div
					class="absolute inset-0 grid gap-2 pointer-events-none opacity-20"
					style="grid-template-columns: repeat({GRID_COLS}, 1fr); grid-template-rows: repeat({maxRow}, {ROW_HEIGHT}px);"
				>
					{#each Array(GRID_COLS * maxRow) as _, i}
						<div class="border border-dashed border-surface-400 rounded"></div>
					{/each}
				</div>

				<!-- Widgets Grid -->
				<div
					bind:this={gridElement}
					class="relative grid gap-2"
					style="grid-template-columns: repeat({GRID_COLS}, 1fr); grid-template-rows: repeat({maxRow}, {ROW_HEIGHT}px);"
					ondragover={handleDragOver}
					ondrop={handleDrop}
					role="grid"
				>
					{#each widgets as widget (widget.id)}
						<div
							class="card bg-white dark:bg-surface-900 shadow-md p-3 cursor-move relative group transition-shadow hover:shadow-lg {isDragging &&
							draggedWidget?.id === widget.id
								? 'opacity-50'
								: ''}"
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
										{widget.display_title ||
											widget.title ||
											widget.metric_instance?.name ||
											'Widget'}
									</h4>
									<p class="text-xs text-surface-500 truncate">
										{getEffectiveChartTypeDisplay(widget)}
									</p>
								</div>
								<div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
									<a
										href="/{widget.chart_type === 'text'
											? 'dashboard-text-widgets'
											: widget.metric_key
												? 'dashboard-builtin-widgets'
												: 'dashboard-widgets'}/{widget.id}/edit?next=/dashboards/{dashboard.id}/layout"
										class="btn btn-sm preset-tonal p-1"
										title={m.edit()}
									>
										<i class="fa-solid fa-pencil text-sm"></i>
									</a>
									<button
										class="btn btn-sm preset-filled-error-500 p-1"
										onclick={() => confirmDeleteWidget(widget)}
										title={m.delete()}
									>
										<i class="fa-solid fa-trash text-sm"></i>
									</button>
								</div>
							</div>

							<!-- Widget Preview -->
							<div
								class="flex-1 bg-surface-100-900 rounded flex items-center justify-center text-surface-400 min-h-[60px]"
							>
								<i
									class="text-4xl fa-solid {widget.chart_type === 'kpi_card'
										? 'fa-square-poll-vertical'
										: widget.chart_type === 'bar'
											? 'fa-chart-bar'
											: widget.chart_type === 'gauge'
												? 'fa-gauge-high'
												: widget.chart_type === 'sparkline'
													? 'fa-chart-area'
													: widget.chart_type === 'table'
														? 'fa-table'
														: widget.chart_type === 'area'
															? 'fa-chart-area'
															: widget.chart_type === 'text'
																? 'fa-font'
																: 'fa-chart-line'}"
								></i>
							</div>

							<!-- Position info -->
							<div
								class="absolute bottom-1 left-1 text-xs text-surface-400 opacity-0 group-hover:opacity-100"
								title="Position: {widget.position_x},{widget.position_y} | Size: {widget.width}x{widget.height} | Min: {getMinDimensions(
									widget.chart_type
								).width}x{getMinDimensions(widget.chart_type).height}"
							>
								{widget.width}x{widget.height} (min: {getMinDimensions(widget.chart_type)
									.width}x{getMinDimensions(widget.chart_type).height})
							</div>

							<!-- Resize handle -->
							<div
								class="absolute bottom-0 right-0 w-5 h-5 cursor-se-resize opacity-0 group-hover:opacity-100 flex items-center justify-center"
								onmousedown={(e) => {
									e.preventDefault();
									e.stopPropagation();

									const startX = e.clientX;
									const startY = e.clientY;
									const startWidth = widget.width || 6;
									const startHeight = widget.height || 2;
									const widgetId = widget.id;

									// Get grid dimensions at start
									const { colWidth } = getGridDimensions();
									const cellWithGap = colWidth + GRID_GAP;
									const rowWithGap = ROW_HEIGHT + GRID_GAP;

									const onMouseMove = (moveEvent: MouseEvent) => {
										moveEvent.preventDefault();
										const deltaX = moveEvent.clientX - startX;
										const deltaY = moveEvent.clientY - startY;

										// Calculate new size based on pixel delta
										const newWidth = startWidth + deltaX / cellWithGap;
										const newHeight = startHeight + deltaY / rowWithGap;

										updateWidgetSize(widgetId, newWidth, newHeight);
									};

									const onMouseUp = () => {
										document.removeEventListener('mousemove', onMouseMove);
										document.removeEventListener('mouseup', onMouseUp);
										document.body.style.cursor = '';
										document.body.style.userSelect = '';
									};

									document.body.style.cursor = 'se-resize';
									document.body.style.userSelect = 'none';
									document.addEventListener('mousemove', onMouseMove);
									document.addEventListener('mouseup', onMouseUp);
								}}
								role="slider"
								aria-label="Resize widget"
								tabindex="0"
							>
								<i
									class="fa-solid fa-up-right-and-down-left-from-center text-xs text-surface-400 rotate-90"
								></i>
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Row Controls -->
			<div class="flex gap-2 mt-2">
				<button
					class="flex-1 py-2 border-2 border-dashed border-surface-300 dark:border-surface-600 rounded-lg text-surface-400 hover:border-primary-500 hover:text-primary-500 transition-colors flex items-center justify-center gap-2"
					onclick={addRow}
				>
					<i class="fa-solid fa-plus"></i>
					{m.addRow()}
				</button>
				{#if canRemoveRow}
					<button
						class="flex-1 py-2 border-2 border-dashed border-surface-300 dark:border-surface-600 rounded-lg text-surface-400 hover:border-error-500 hover:text-error-500 transition-colors flex items-center justify-center gap-2"
						onclick={removeRow}
					>
						<i class="fa-solid fa-minus"></i>
						{m.removeRow()}
					</button>
				{/if}
			</div>
		{:else}
			<div class="flex flex-col items-center justify-center min-h-[400px] text-surface-500">
				<i class="fa-solid fa-chart-line text-6xl mb-4"></i>
				<p class="mb-4">{m.noWidgetsYet()}</p>
				<button class="btn preset-filled-primary-500" onclick={openAddBuiltinWidgetModal}>
					<i class="fa-solid fa-chart-simple"></i>
					{m.addFirstWidget()}
				</button>
			</div>
		{/if}
	</div>
</div>
