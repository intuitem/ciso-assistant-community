<script lang="ts">
	import GanttChart from '$lib/components/Gantt/GanttChart.svelte';
	import type { GanttItem } from '$lib/components/Gantt/GanttChart.svelte';
	import { pageTitle } from '$lib/utils/stores';

	let { data } = $props();

	$pageTitle = 'Gantt Chart';

	// --- Category config ---
	const CATEGORIES = [
		{
			key: 'appliedControls',
			label: 'Applied Controls',
			color: '#6366f1', // indigo
			urlPrefix: 'applied-controls'
		},
		{
			key: 'complianceAssessments',
			label: 'Compliance Assessments',
			color: '#0ea5e9', // sky
			urlPrefix: 'compliance-assessments'
		},
		{
			key: 'riskAssessments',
			label: 'Risk Assessments',
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
	function buildItems(): { items: GanttItem[]; noDateCount: number } {
		const items: GanttItem[] = [];
		let noDateCount = 0;

		const catConfig = Object.fromEntries(CATEGORIES.map((c) => [c.key, c]));

		// Applied Controls: start_date + eta → bar with progress; eta only → milestone
		if (enabledCategories.has('appliedControls')) {
			for (const ac of data.appliedControls) {
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
					color: catConfig.appliedControls.color
				});
			}
		}

		// Compliance Assessments: eta + due_date → bar; eta only → milestone
		if (enabledCategories.has('complianceAssessments')) {
			for (const ca of data.complianceAssessments) {
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
					color: catConfig.complianceAssessments.color
				});
			}
		}

		// Risk Assessments: eta + due_date → bar; eta only → milestone
		if (enabledCategories.has('riskAssessments')) {
			for (const ra of data.riskAssessments) {
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
					color: catConfig.riskAssessments.color
				});
			}
		}

		return { items, noDateCount };
	}

	// Use $derived to react to filter changes
	let result = $derived(buildItems());
	let ganttItems = $derived(result.items);
	let noDateCount = $derived(result.noDateCount);

	// Available folders (only those that have data)
	let availableFolders = $derived.by(() => {
		const ids = new Set<string>();
		for (const list of [data.appliedControls, data.complianceAssessments, data.riskAssessments]) {
			for (const obj of list) {
				const fid = obj.folder?.id ?? obj.folder;
				if (fid) ids.add(fid);
			}
		}
		return Array.from(ids)
			.map((id) => ({ id, name: folderMap.get(id) ?? 'Unknown' }))
			.sort((a, b) => a.name.localeCompare(b.name));
	});
</script>

<div class="p-6 space-y-4">
	<div class="flex items-center justify-between">
		<h2 class="h3 font-bold">Gantt Chart</h2>
	</div>

	<!-- Toolbar: Zoom + Filters -->
	<div class="flex flex-wrap items-center gap-4">
		<!-- Zoom selector -->
		<div class="flex items-center gap-1 bg-surface-100 rounded-lg p-1">
			<span class="text-xs font-semibold text-surface-500 px-2">Zoom</span>
			{#each ['weekly', 'monthly', 'yearly'] as level}
				<button
					class="px-3 py-1 text-xs font-medium rounded-md transition-colors {zoom === level
						? 'bg-white shadow-sm text-primary-700'
						: 'text-surface-500 hover:text-surface-700'}"
					onclick={() => (zoom = level as 'weekly' | 'monthly' | 'yearly')}
				>
					{level.charAt(0).toUpperCase() + level.slice(1)}
				</button>
			{/each}
		</div>

		<!-- Category toggles -->
		<div class="flex items-center gap-2">
			<span class="text-xs font-semibold text-surface-500">Show</span>
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

		<!-- Folder filter -->
		{#if availableFolders.length > 1}
			<div class="flex items-center gap-2">
				<span class="text-xs font-semibold text-surface-500">Domains</span>
				<div class="flex flex-wrap gap-1">
					{#each availableFolders as folder}
						<button
							class="px-2 py-0.5 text-xs rounded-md border transition-colors {selectedFolders.has(
								folder.id
							)
								? 'bg-primary-100 border-primary-400 text-primary-700'
								: selectedFolders.size === 0
									? 'bg-surface-50 border-surface-200 text-surface-600'
									: 'bg-white border-surface-200 text-surface-400'}"
							onclick={() => toggleFolder(folder.id)}
						>
							{folder.name}
						</button>
					{/each}
					{#if selectedFolders.size > 0}
						<button
							class="px-2 py-0.5 text-xs text-surface-400 hover:text-surface-600"
							onclick={() => (selectedFolders = new Set())}
						>
							Clear
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- No-date warning -->
	{#if noDateCount > 0}
		<div
			class="flex items-center gap-2 px-3 py-2 bg-warning-50 border border-warning-200 rounded-lg text-xs text-warning-700"
		>
			<i class="fa-solid fa-triangle-exclamation"></i>
			{noDateCount} object{noDateCount > 1 ? 's' : ''} with no date information {noDateCount > 1
				? 'are'
				: 'is'} not shown.
		</div>
	{/if}

	<!-- Chart or empty state -->
	{#if ganttItems.length === 0}
		<div class="flex flex-col items-center justify-center py-16 text-surface-400">
			<i class="fa-solid fa-chart-gantt text-4xl mb-3"></i>
			<p class="text-sm">No items to display. Adjust your filters or add dates to your objects.</p>
		</div>
	{:else}
		<GanttChart items={ganttItems} {zoom} />
	{/if}
</div>
