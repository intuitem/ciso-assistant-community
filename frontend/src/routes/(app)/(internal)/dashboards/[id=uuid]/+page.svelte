<script lang="ts">
	import type { PageData } from './$types';
	import DashboardGrid from '#lib/components/Dashboard/DashboardGrid.svelte';
	import MultiSelect from 'svelte-multiselect';
	import { m } from '#paraglide/messages.js';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const dashboard = $derived(data.data);
	const widgets = $derived(data.widgets || []);

	let selectedTitles: string[] = $state([]);

	const filteredWidgets = $derived.by(() => {
		if (selectedTitles.length === 0) {
			return widgets;
		}

		// All dashboards have a fixed number of columns (12 columns).
		const X_LIMIT = 12;

		/** (Only contain a few properties of all the existing one in a widget). */
		interface Widget {
			position_x: number;
			position_y: number;
			width: number;
			height: number;
		}

		const filteredWidgets: Widget[] = widgets.filter(({ title }) => selectedTitles.includes(title));

		let finalWidgets: Widget[] = [];
		let currentX = 0;
		let currentY = 0;

		for (const widget of filteredWidgets) {
			// We clone it to not modify the original widget's data.
			const clonedWidget = structuredClone(widget);

			const endX = currentX + clonedWidget.width;

			// If there's not enough space in the current widget line we jump to the next line.
			if (endX > X_LIMIT) {
				const currentLineWidgets = finalWidgets.filter(({ position_y }) => position_y === currentY);
				const currentLineHeights = currentLineWidgets.map(({ height }) => height);
				const maxLineHeight = Math.max(0, ...currentLineHeights);
				// Set the cursor(currentX,currentY) back to the beginning of the next line (X=0, Y=next line) .
				currentX = 0;
				// Make sure the next widget line is above all the widgets in the previous widget line.
				currentY += maxLineHeight;
			}

			clonedWidget.position_x = currentX;
			clonedWidget.position_y = currentY;

			currentX = currentX + clonedWidget.width;

			finalWidgets.push(clonedWidget);
		}

		return finalWidgets;
	});

	const widgetTitles = $derived.by(() => {
		const widgetTitleList = widgets
			.filter(
				// Adding the "text"-widgets in the filter options would be useless and confusing.
				({ chart_type, title }) => chart_type !== 'text' && Boolean(title)
			)
			.map(({ title }) => title);
		const uniqueWidgetTitleList = [...new Set(widgetTitleList)];
		const sortedTitles = uniqueWidgetTitleList.toSorted((a, b) => a.localeCompare(b));

		return sortedTitles;
	});
</script>

<div class="p-6 space-y-4 dashboard-print">
	<!-- Header -->
	<div class="flex justify-between items-start gap-2">
		<div class="flex items-start grow gap-4">
			<a href="/dashboards" class="btn preset-tonal no-print">
				<i class="fa-solid fa-arrow-left"></i>
				{m.back()}
			</a>
			<h1 class="text-2xl font-bold">{dashboard.name}</h1>
			{#if dashboard.description}
				<span class="text-surface-500">- {dashboard.description}</span>
			{/if}
		</div>
		<div class="flex justify-end items-start gap-2 no-print">
			{#if widgetTitles.length > 0}
				<MultiSelect
					bind:selected={selectedTitles}
					options={widgetTitles}
					placeholder={m.widgets()}
					aria-label={m.widgets()}
					closeDropdownOnSelect={false}
					outerDivClass="!input !bg-surface-100-900 !px-2 !flex min-w-64 max-w-1/2!"
				/>
			{/if}
			<button class="btn preset-tonal" onclick={() => window.print()}>
				<i class="fa-solid fa-file-pdf"></i>
				{m.exportPdf()}
			</button>
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

	<!-- Widgets Grid -->
	<div class="bg-surface-50-950 rounded-lg p-4 -mx-2">
		{#if filteredWidgets.length > 0}
			<DashboardGrid widgets={filteredWidgets} />
		{:else}
			<div class="card p-12 bg-surface-50-950 text-center">
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

<style>
	@media print {
		.no-print,
		:global(body:has(.dashboard-print) .sidebar),
		:global(body:has(.dashboard-print) #page-header),
		:global(body:has(.dashboard-print) header:not(main *)) {
			display: none !important;
		}

		:global(body:has(.dashboard-print) main) {
			padding: 0 !important;
			margin: 0 !important;
		}

		:global(body:has(.dashboard-print)) {
			print-color-adjust: exact;
			-webkit-print-color-adjust: exact;
		}
	}
</style>
