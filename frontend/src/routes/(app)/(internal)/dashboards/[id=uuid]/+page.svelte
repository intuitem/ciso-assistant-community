<script lang="ts">
	import type { PageData } from './$types';
	import DashboardGrid from '#lib/components/Dashboard/DashboardGrid.svelte';
	import { m } from '#paraglide/messages.js';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	const dashboard = $derived(data.data);
	const widgets = $derived(data.widgets || []);
</script>

<div class="p-6 space-y-4 dashboard-print">
	<!-- Header -->
	<div class="flex justify-between items-center">
		<div class="flex items-center gap-4">
			<a href="/dashboards" class="btn preset-tonal no-print">
				<i class="fa-solid fa-arrow-left"></i>
				{m.back()}
			</a>
			<h1 class="text-2xl font-bold">{dashboard.name}</h1>
			{#if dashboard.description}
				<span class="text-surface-500">- {dashboard.description}</span>
			{/if}
		</div>
		<div class="flex items-center gap-2 no-print">
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
		{#if widgets.length > 0}
			<DashboardGrid {widgets} />
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
