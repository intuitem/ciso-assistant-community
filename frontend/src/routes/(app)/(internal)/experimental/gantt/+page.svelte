<script lang="ts">
	import GanttChart from '$lib/components/Gantt/GanttChart.svelte';
	import type { GanttItem } from '$lib/components/Gantt/GanttChart.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	let { data } = $props();

	$pageTitle = m.ganttChart();

	// --- Category config ---
	const CATEGORIES = [
		{
			key: 'appliedControls',
			label: m.appliedControls(),
			color: '#6366f1', // indigo
			urlPrefix: 'applied-controls'
		},
		{
			key: 'complianceAssessments',
			label: m.complianceAssessments(),
			color: '#0ea5e9', // sky
			urlPrefix: 'compliance-assessments'
		},
		{
			key: 'riskAssessments',
			label: m.riskAssessments(),
			color: '#f97316', // orange
			urlPrefix: 'risk-assessments'
		}
	] as const;

	type CategoryKey = (typeof CATEGORIES)[number]['key'];

	// --- Folder lookup ---
	const folderMap = new Map<string, string>();
	for (const f of data.folders) {
		folderMap.set(f.id, f.name ?? f.str ?? 'Unknown');
	}

	// --- Filters ---
	let enabledCategories = $state<Set<CategoryKey>>(new Set(CATEGORIES.map((c) => c.key)));
	let selectedFolders = $state<Set<string>>(new Set());
	let zoom = $state<'weekly' | 'monthly' | 'yearly'>('monthly');

	const ZOOM_LEVELS = [
		{ value: 'weekly', label: m.weekly() },
		{ value: 'monthly', label: m.monthly() },
		{ value: 'yearly', label: m.yearly() }
	] as const;

	function toggleCategory(key: CategoryKey) {
		const next = new Set(enabledCategories);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		enabledCategories = next;
	}

	function toggleFolder(id: string) {
		const next = new Set(selectedFolders);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedFolders = next;
	}

	// --- Transform raw data into GanttItems ---
	function buildItems(sourceData: {
		appliedControls: any[];
		complianceAssessments: any[];
		riskAssessments: any[];
	}): { items: GanttItem[]; noDateCount: number } {
		const items: GanttItem[] = [];
		let noDateCount = 0;

		const catConfig = Object.fromEntries(CATEGORIES.map((c) => [c.key, c]));
		const getOwners = (obj: any): string[] =>
			(obj.owner ?? obj.owners ?? []).map((o: any) => o.str ?? o.name ?? '').filter(Boolean);

		// Applied Controls: start_date + eta → bar with progress; eta only → milestone
		if (enabledCategories.has('appliedControls')) {
			for (const ac of sourceData.appliedControls) {
				const folderId = ac.folder?.id ?? ac.folder;
				if (selectedFolders.size > 0 && !selectedFolders.has(folderId)) continue;
				const start = ac.start_date ? new Date(ac.start_date) : null;
				const eta = ac.eta ? new Date(ac.eta) : null;
				if (!start && !eta) {
					noDateCount++;
					continue;
				}
				items.push({
					id: ac.id,
					name: ac.name ?? ac.str ?? '(unnamed)',
					startDate: start,
					endDate: eta,
					progress: ac.progress_field ?? 0,
					type: start && eta ? 'bar' : 'milestone',
					category: 'appliedControls',
					categoryLabel: catConfig.appliedControls.label,
					folder: folderMap.get(folderId) ?? 'Unknown',
					folderId,
					href: `/applied-controls/${ac.id}`,
					color: catConfig.appliedControls.color,
					owners: getOwners(ac)
				});
			}
		}

		// Compliance Assessments: eta + due_date → bar; eta only → milestone
		if (enabledCategories.has('complianceAssessments')) {
			for (const ca of sourceData.complianceAssessments) {
				const folderId = ca.folder?.id ?? ca.folder;
				if (selectedFolders.size > 0 && !selectedFolders.has(folderId)) continue;
				const eta = ca.eta ? new Date(ca.eta) : null;
				const due = ca.due_date ? new Date(ca.due_date) : null;
				const start = eta && due ? (eta < due ? eta : due) : null;
				const end = eta && due ? (eta >= due ? eta : due) : (eta ?? due);
				if (!start && !end) {
					noDateCount++;
					continue;
				}
				items.push({
					id: ca.id,
					name: ca.name ?? ca.str ?? '(unnamed)',
					startDate: start,
					endDate: end,
					progress: ca.progress ?? 0,
					type: start && end ? 'bar' : 'milestone',
					category: 'complianceAssessments',
					categoryLabel: catConfig.complianceAssessments.label,
					folder: folderMap.get(folderId) ?? 'Unknown',
					folderId,
					href: `/compliance-assessments/${ca.id}`,
					color: catConfig.complianceAssessments.color,
					owners: getOwners(ca)
				});
			}
		}

		// Risk Assessments: eta + due_date → bar; eta only → milestone
		if (enabledCategories.has('riskAssessments')) {
			for (const ra of sourceData.riskAssessments) {
				const folderId = ra.folder?.id ?? ra.folder;
				if (selectedFolders.size > 0 && !selectedFolders.has(folderId)) continue;
				const eta = ra.eta ? new Date(ra.eta) : null;
				const due = ra.due_date ? new Date(ra.due_date) : null;
				const start = eta && due ? (eta < due ? eta : due) : null;
				const end = eta && due ? (eta >= due ? eta : due) : (eta ?? due);
				if (!start && !end) {
					noDateCount++;
					continue;
				}
				items.push({
					id: ra.id,
					name: ra.name ?? ra.str ?? '(unnamed)',
					startDate: start,
					endDate: end,
					progress: 0,
					type: start && end ? 'bar' : 'milestone',
					category: 'riskAssessments',
					categoryLabel: catConfig.riskAssessments.label,
					folder: folderMap.get(folderId) ?? 'Unknown',
					folderId,
					href: `/risk-assessments/${ra.id}`,
					color: catConfig.riskAssessments.color,
					owners: getOwners(ra)
				});
			}
		}

		return { items, noDateCount };
	}
</script>

<div class="p-6 space-y-4">
	<div class="flex items-center justify-between">
		<h2 class="h3 font-bold">{m.ganttChart()}</h2>
	</div>

	<!-- Toolbar: Zoom + Category filters (always visible) -->
	<div class="flex flex-wrap items-center gap-4">
		<!-- Zoom selector -->
		<div class="flex items-center gap-1 bg-surface-100 rounded-lg p-1">
			<span class="text-xs font-semibold text-surface-500 px-2">{m.zoom()}</span>
			{#each ZOOM_LEVELS as level}
				<button
					class="px-3 py-1 text-xs font-medium rounded-md transition-colors {zoom === level.value
						? 'bg-white shadow-sm text-primary-700'
						: 'text-surface-500 hover:text-surface-700'}"
					onclick={() => (zoom = level.value as 'weekly' | 'monthly' | 'yearly')}
				>
					{level.label}
				</button>
			{/each}
		</div>

		<!-- Category toggles -->
		<div class="flex items-center gap-2">
			<span class="text-xs font-semibold text-surface-500">{m.show()}</span>
			{#each CATEGORIES as cat}
				<button
					class="flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-full border transition-colors {enabledCategories.has(
						cat.key
					)
						? 'border-transparent text-white'
						: 'border-surface-300 text-surface-400 bg-white'}"
					style={enabledCategories.has(cat.key) ? `background-color: ${cat.color}` : ''}
					onclick={() => toggleCategory(cat.key)}
				>
					{#if enabledCategories.has(cat.key)}
						<i class="fa-solid fa-check text-[10px]"></i>
					{/if}
					{cat.label}
				</button>
			{/each}
		</div>
	</div>

	<!-- Await streamed data -->
	{#await data.ganttData}
		<div class="flex flex-col items-center justify-center py-24 text-surface-400 gap-4">
			<i class="fa-solid fa-spinner fa-spin text-4xl text-primary-500"></i>
			<p class="text-sm">{m.loadingTimelineData()}</p>
		</div>
	{:then ganttData}
		{@const result = buildItems(ganttData)}
		{@const ganttItems = result.items}
		{@const noDateCount = result.noDateCount}
		{@const availableFolders = (() => {
			const ids = new Set();
			for (const item of ganttItems) ids.add(item.folderId);
			return Array.from(ids)
				.map((id) => ({ id, name: folderMap.get(id as string) ?? 'Unknown' }))
				.sort((a, b) => a.name.localeCompare(b.name));
		})()}

		<!-- Folder filter (only after data loads, only if multiple domains) -->
		{#if availableFolders.length > 1}
			<div class="flex items-center gap-2">
				<span class="text-xs font-semibold text-surface-500">{m.domains()}</span>
				<div class="flex flex-wrap gap-1">
					{#each availableFolders as folder}
						<button
							class="px-2 py-0.5 text-xs rounded-md border transition-colors {selectedFolders.has(
								folder.id as string
							)
								? 'bg-primary-100 border-primary-400 text-primary-700'
								: selectedFolders.size === 0
									? 'bg-surface-50 border-surface-200 text-surface-600'
									: 'bg-white border-surface-200 text-surface-400'}"
							onclick={() => toggleFolder(folder.id as string)}
						>
							{folder.name}
						</button>
					{/each}
					{#if selectedFolders.size > 0}
						<button
							class="px-2 py-0.5 text-xs text-surface-400 hover:text-surface-600"
							onclick={() => (selectedFolders = new Set())}
						>
							{m.clear()}
						</button>
					{/if}
				</div>
			</div>
		{/if}

		<!-- No-date warning -->
		{#if noDateCount > 0}
			<div
				class="flex items-center gap-2 px-3 py-2 bg-warning-50 border border-warning-200 rounded-lg text-xs text-warning-700"
			>
				<i class="fa-solid fa-triangle-exclamation"></i>
				{m.objectsWithNoDateNotShown({ count: noDateCount })}
			</div>
		{/if}

		<!-- Chart or empty state -->
		{#if ganttItems.length === 0}
			<div class="flex flex-col items-center justify-center py-16 text-surface-400">
				<i class="fa-solid fa-chart-gantt text-4xl mb-3"></i>
				<p class="text-sm">{m.noItemsToDisplayAdjustFilters()}</p>
			</div>
		{:else}
			<GanttChart items={ganttItems} {zoom} />
		{/if}
	{:catch}
		<div
			class="flex items-center gap-2 px-3 py-2 bg-error-50 border border-error-200 rounded-lg text-xs text-error-700"
		>
			<i class="fa-solid fa-circle-exclamation"></i>
			{m.failedToLoadTimelineData()}
		</div>
	{/await}
</div>
