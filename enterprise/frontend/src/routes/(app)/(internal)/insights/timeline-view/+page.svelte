<script lang="ts">
	import GanttChart from '#lib/components/Gantt/GanttChart.svelte';
	import type { GanttItem } from '#lib/components/Gantt/GanttChart.svelte';
	import AutocompleteSelect from '#lib/components/Forms/AutocompleteSelect.svelte';
	import { pageTitle } from '#lib/utils/stores.js';
	import { m } from '#paraglide/messages.js';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';

	let { data } = $props();

	$pageTitle = m.ganttChart();

	// --- Category config ---
	const CATEGORIES = [
		{
			key: 'appliedControls',
			label: m.appliedControls(),
			color: '#6366f1' // indigo
		},
		{
			key: 'complianceAssessments',
			label: m.complianceAssessments(),
			color: '#0ea5e9' // sky
		},
		{
			key: 'riskAssessments',
			label: m.riskAssessments(),
			color: '#f97316' // orange
		},
		{
			key: 'businessImpactAnalyses',
			label: m.businessImpactAnalysis(),
			color: '#14b8a6' // teal
		},
		{
			key: 'findingsAssessments',
			label: m.findingsAssessments(),
			color: '#ef4444' // red
		},
		{
			key: 'securityExceptions',
			label: m.securityExceptions(),
			color: '#a855f7' // purple
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
	let useCreatedAtAsStart = $state(false);
	// Narrows applied controls to those linked to a selected risk scenario
	// (existing or additional measure). Other categories are left as they are.
	let selectedScenarios = $state<Set<string>>(new Set());
	let ganttRef: ReturnType<typeof GanttChart> | undefined = $state();

	// The scenario picker loads its options server-side, so it needs a form.
	const scenarioFilterSchema = z.object({
		risk_scenarios: z.array(z.string()).optional().nullable()
	});
	const scenarioFilterForm = superForm(
		defaults({ risk_scenarios: [] }, zod(scenarioFilterSchema)),
		{
			SPA: true,
			validators: zod(scenarioFilterSchema),
			dataType: 'json',
			invalidateAll: false,
			applyAction: false,
			resetForm: false,
			taintedMessage: false,
			validationMethod: 'auto'
		}
	);

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
		businessImpactAnalyses: any[];
		findingsAssessments: any[];
		securityExceptions: any[];
	}): { items: GanttItem[]; noDateCount: number; allFolderIds: Set<string> } {
		const items: GanttItem[] = [];
		let noDateCount = 0;
		const allFolderIds = new Set<string>();

		const catConfig = Object.fromEntries(CATEGORIES.map((c) => [c.key, c]));
		// Parse any date/datetime string to a Date at midnight UTC (no timezone drift)
		const parseDate = (v: string | null | undefined): Date | null => {
			if (!v) return null;
			// Take only the YYYY-MM-DD part to avoid timezone issues
			const d = new Date(v.substring(0, 10) + 'T00:00:00');
			return isNaN(d.getTime()) ? null : d;
		};
		const getOwners = (obj: any): string[] =>
			(obj.owner ?? obj.owners ?? obj.authors ?? [])
				.map((o: any) => o.str ?? o.name ?? '')
				.filter(Boolean);

		// Applied Controls: start_date + eta → bar with progress; eta only → milestone
		if (enabledCategories.has('appliedControls')) {
			for (const ac of sourceData.appliedControls) {
				if (
					selectedScenarios.size > 0 &&
					!(ac.risk_scenarios ?? []).some((id: string) => selectedScenarios.has(id))
				)
					continue;
				const folderId = ac.folder?.id ?? ac.folder;
				const start = parseDate(ac.start_date);
				const eta = parseDate(ac.eta);
				if (!start && !eta) {
					noDateCount++;
					continue;
				}
				allFolderIds.add(folderId);
				if (selectedFolders.size > 0 && !selectedFolders.has(folderId)) continue;
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

		// Assessment-type models: no real start_date, so eta/due_date are milestones
		const assessmentCategories = [
			{
				key: 'complianceAssessments' as CategoryKey,
				data: sourceData.complianceAssessments,
				hrefPrefix: '/compliance-assessments',
				getProgress: (obj: any) => obj.progress ?? 0
			},
			{
				key: 'riskAssessments' as CategoryKey,
				data: sourceData.riskAssessments,
				hrefPrefix: '/risk-assessments',
				getProgress: (_: any) => -1
			},
			{
				key: 'businessImpactAnalyses' as CategoryKey,
				data: sourceData.businessImpactAnalyses,
				hrefPrefix: '/business-impact-analysis',
				getProgress: (_: any) => -1
			},
			{
				key: 'findingsAssessments' as CategoryKey,
				data: sourceData.findingsAssessments,
				hrefPrefix: '/findings-assessments',
				getProgress: (_: any) => -1
			}
		];

		for (const { key, data, hrefPrefix, getProgress } of assessmentCategories) {
			if (!enabledCategories.has(key)) continue;
			for (const obj of data) {
				const folderId = obj.folder?.id ?? obj.folder;
				const date = parseDate(obj.eta) ?? parseDate(obj.due_date);
				if (!date) {
					noDateCount++;
					continue;
				}
				allFolderIds.add(folderId);
				if (selectedFolders.size > 0 && !selectedFolders.has(folderId)) continue;
				const createdAt = useCreatedAtAsStart ? parseDate(obj.created_at) : null;
				// Only use created_at as start if it's before the target date
				const startDate = createdAt && createdAt < date ? createdAt : null;
				const hasRange = startDate !== null;
				items.push({
					id: obj.id,
					name: obj.name ?? obj.str ?? '(unnamed)',
					startDate,
					endDate: date,
					progress: getProgress(obj),
					type: hasRange ? 'bar' : 'milestone',
					category: key,
					categoryLabel: catConfig[key].label,
					folder: folderMap.get(folderId) ?? 'Unknown',
					folderId,
					href: `${hrefPrefix}/${obj.id}`,
					color: catConfig[key].color,
					owners: getOwners(obj)
				});
			}
		}

		// Security Exceptions: expiration_date as milestone, created_at as optional start
		if (enabledCategories.has('securityExceptions')) {
			for (const se of sourceData.securityExceptions) {
				const folderId = se.folder?.id ?? se.folder;
				const date = parseDate(se.expiration_date);
				if (!date) {
					noDateCount++;
					continue;
				}
				allFolderIds.add(folderId);
				if (selectedFolders.size > 0 && !selectedFolders.has(folderId)) continue;
				const createdAt = useCreatedAtAsStart ? parseDate(se.created_at) : null;
				const startDate = createdAt && createdAt < date ? createdAt : null;
				const hasRange = startDate !== null;
				items.push({
					id: se.id,
					name: se.name ?? se.str ?? '(unnamed)',
					startDate,
					endDate: date,
					progress: -1,
					type: hasRange ? 'bar' : 'milestone',
					category: 'securityExceptions',
					categoryLabel: catConfig.securityExceptions.label,
					folder: folderMap.get(folderId) ?? 'Unknown',
					folderId,
					href: `/security-exceptions/${se.id}`,
					color: catConfig.securityExceptions.color,
					owners: getOwners(se)
				});
			}
		}

		return { items, noDateCount, allFolderIds };
	}
</script>

<div class="p-6 space-y-4">
	<!-- Toolbar: Zoom + Category filters (always visible) -->
	<div class="flex flex-wrap items-center gap-4">
		<!-- Zoom selector -->
		<div class="flex items-center gap-1 bg-surface-100-900 rounded-lg p-1">
			<span class="text-xs font-semibold text-surface-500 px-2">{m.zoom()}</span>
			{#each ZOOM_LEVELS as level}
				<button
					class="px-3 py-1 text-xs font-medium rounded-md transition-colors {zoom === level.value
						? 'bg-surface-50-950 shadow-sm text-primary-700-300'
						: 'text-surface-500 hover:text-surface-700-300'}"
					onclick={() => (zoom = level.value as 'weekly' | 'monthly' | 'yearly')}
				>
					{level.label}
				</button>
			{/each}
			<button
				class="px-3 py-1 text-xs font-medium rounded-md text-error-600-400 hover:bg-error-50-950 transition-colors"
				onclick={() => ganttRef?.scrollToToday()}
			>
				<i class="fa-solid fa-crosshairs mr-1"></i>{m.today()}
			</button>
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
						: 'border-surface-300-700 text-surface-500 bg-surface-50-950'}"
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

		<!-- Creation date as start toggle -->
		<label class="flex items-center gap-1.5 cursor-pointer">
			<input
				type="checkbox"
				bind:checked={useCreatedAtAsStart}
				class="w-3.5 h-3.5 rounded border-surface-300-700 text-primary-600"
			/>
			<span class="text-xs text-surface-500">{m.useCreationDateAsStart()}</span>
		</label>

		<!-- Risk scenario filter (applied controls only) -->
		<div class="w-80" data-testid="timeline-scenario-filter">
			<AutocompleteSelect
				form={scenarioFilterForm}
				field="risk_scenarios"
				label={m.riskScenarios()}
				helpText={m.timelineScenarioFilterHelpText()}
				optionsEndpoint="risk-scenarios"
				optionsLabelField="auto"
				optionsExtraFields={[['risk_assessment', 'str']]}
				lazy={true}
				multiple={true}
				portalDropdown={true}
				onChange={(value) =>
					(selectedScenarios = new Set(Array.isArray(value) ? value : value ? [value] : []))}
			/>
		</div>
	</div>

	<!-- Await streamed data -->
	{#await data.ganttData}
		<div class="flex flex-col items-center justify-center py-24 text-surface-500 gap-4">
			<i class="fa-solid fa-spinner fa-spin text-4xl text-primary-500"></i>
			<p class="text-sm">{m.loadingTimelineData()}</p>
		</div>
	{:then ganttData}
		{#if ganttData.error}
			<div
				class="flex items-center gap-2 px-3 py-2 bg-error-50-950 border border-error-200-800 rounded-lg text-xs text-error-700-300"
			>
				<i class="fa-solid fa-circle-exclamation"></i>
				{m.failedToLoadTimelineData()}
			</div>
		{:else}
			{@const result = buildItems(ganttData)}
			{@const ganttItems = result.items}
			{@const noDateCount = result.noDateCount}
			{@const availableFolders = Array.from(new Set([...result.allFolderIds, ...selectedFolders]))
				.map((id) => ({ id, name: folderMap.get(id) ?? 'Unknown' }))
				.sort((a, b) => a.name.localeCompare(b.name))}

			<!-- Folder filter (only after data loads, only if multiple domains or a selection).
			     Selected domains stay listed even when the other filters leave them empty,
			     so they can always be cleared. -->
			{#if availableFolders.length > 1 || selectedFolders.size > 0}
				<div class="flex items-center gap-2">
					<span class="text-xs font-semibold text-surface-500">{m.domains()}</span>
					<div class="flex flex-wrap gap-1">
						{#each availableFolders as folder}
							<button
								class="px-2 py-0.5 text-xs rounded-md border transition-colors {selectedFolders.has(
									folder.id
								)
									? 'bg-primary-100-900 border-primary-400-600 text-primary-700-300'
									: selectedFolders.size === 0
										? 'bg-surface-50-950 border-surface-200-800 text-surface-600-400'
										: 'bg-surface-50-950 border-surface-200-800 text-surface-500'}"
								onclick={() => toggleFolder(folder.id)}
							>
								{folder.name}
							</button>
						{/each}
						{#if selectedFolders.size > 0}
							<button
								class="px-2 py-0.5 text-xs text-surface-500 hover:text-surface-600-400"
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
					class="flex items-center gap-2 px-3 py-2 bg-warning-50-950 border border-warning-200-800 rounded-lg text-xs text-warning-700-300"
				>
					<i class="fa-solid fa-triangle-exclamation"></i>
					{m.objectsWithNoDateNotShown({ count: noDateCount })}
				</div>
			{/if}

			<!-- Chart or empty state -->
			{#if ganttItems.length === 0}
				<div class="flex flex-col items-center justify-center py-16 text-surface-500">
					<i class="fa-solid fa-chart-gantt text-4xl mb-3"></i>
					<p class="text-sm">{m.noItemsToDisplayAdjustFilters()}</p>
				</div>
			{:else}
				<GanttChart bind:this={ganttRef} items={ganttItems} {zoom} />
			{/if}
		{/if}
	{:catch}
		<div
			class="flex items-center gap-2 px-3 py-2 bg-error-50-950 border border-error-200-800 rounded-lg text-xs text-error-700-300"
		>
			<i class="fa-solid fa-circle-exclamation"></i>
			{m.failedToLoadTimelineData()}
		</div>
	{/await}
</div>
