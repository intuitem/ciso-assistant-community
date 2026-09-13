<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Create local mutable copy of applied controls to avoid SvelteKit data reload issues
	let appliedControls = $state([...data.applied_controls]);

	// Per-swimlane totals from the aggregate endpoint. The board renders these
	// even for swimlanes whose cards have not been fetched, so the numbers on
	// screen are the real ones rather than "what happens to be loaded".
	type LaneStats = {
		folder: Record<string, any>;
		count: number;
		perStatus: Record<string, number>;
	};
	let laneStats: Record<string, LaneStats> = $state(
		Object.fromEntries(
			(data.counts?.results ?? []).map((entry: any) => [
				entry.folder.id,
				{ folder: entry.folder, count: entry.count, perStatus: { ...entry.per_status } }
			])
		)
	);
	const swimlanes = $derived(
		Object.values(laneStats).sort((a, b) =>
			String(a.folder.str ?? '').localeCompare(String(b.folder.str ?? ''))
		)
	);
	const totalCount = $derived(Object.values(laneStats).reduce((sum, lane) => sum + lane.count, 0));

	// How many cards the board is willing to render without being asked. A
	// preloaded board is already under it; past it, swimlanes open on demand so
	// a big board costs one aggregate request instead of one request per 200 rows.
	const AUTO_EXPAND_BUDGET = 600;

	// Smallest lanes first, so the budget buys as many open swimlanes as it can
	// rather than being spent on one large one.
	function lanesWithinBudget(): string[] {
		const ordered = Object.values(laneStats).sort((a, b) => a.count - b.count);
		const open: string[] = [];
		let budget = AUTO_EXPAND_BUDGET;
		for (const lane of ordered) {
			if (lane.count > budget) break;
			budget -= lane.count;
			open.push(lane.folder.id);
		}
		return open;
	}

	// A small board arrives whole, so every swimlane is already loaded and open.
	const initiallyOpen = data.preloaded ? Object.keys(laneStats) : lanesWithinBudget();

	let loadedFolders: Set<string> = $state(new Set(data.preloaded ? Object.keys(laneStats) : []));
	let loadingFolders: Set<string> = $state(new Set());

	// Fetch the cards for lanes the budget opened. Sequential: these are one
	// user's page load, not a reason to open several backend slots at once.
	onMount(async () => {
		if (data.preloaded) return;
		// Group the opened lanes into page-sized requests; a lane bigger than one
		// page gets its first page here and its "load more" button for the rest.
		let batch: string[] = [];
		let batched = 0;
		for (const folderId of initiallyOpen) {
			const count = laneStats[folderId]?.count ?? 0;
			if (batch.length > 0 && batched + count > data.pageSize) {
				await loadLaneBatch(batch);
				batch = [];
				batched = 0;
			}
			batch.push(folderId);
			batched += count;
		}
		await loadLaneBatch(batch);
	});

	function loadedCountForFolder(folderId: string): number {
		return appliedControls.filter((control: any) => control.folder?.id === folderId).length;
	}

	async function loadFolderPage(folderId: string, offset: number) {
		if (loadingFolders.has(folderId)) return;
		loadingFolders = new Set(loadingFolders).add(folderId);
		try {
			const params = new URLSearchParams(data.filterQuery);
			// Replaces any folder filter inherited from the list view: this request
			// is for one swimlane, and the aggregate already excluded the rest.
			params.set('folder', folderId);
			params.set('offset', String(offset));
			params.set('limit', String(data.pageSize));
			const response = await fetch(`/${data.URLModel}?${params.toString()}`);
			if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
			const body = await response.json();
			const known = new Set(appliedControls.map((control: any) => control.id));
			appliedControls = [
				...appliedControls,
				...(body.results ?? []).filter((row: any) => !known.has(row.id))
			];
			loadedFolders = new Set(loadedFolders).add(folderId);
		} catch (error) {
			console.error('Error loading swimlane:', error);
		} finally {
			const next = new Set(loadingFolders);
			next.delete(folderId);
			loadingFolders = next;
		}
	}

	// The folder filter takes repeated values, so lanes that fit in a single page
	// are opened with one request rather than one apiece.
	async function loadLaneBatch(folderIds: string[]) {
		if (folderIds.length === 0) return;
		loadingFolders = new Set([...loadingFolders, ...folderIds]);
		try {
			const params = new URLSearchParams(data.filterQuery);
			params.delete('folder');
			for (const folderId of folderIds) params.append('folder', folderId);
			params.set('offset', '0');
			params.set('limit', String(data.pageSize));
			const response = await fetch(`/${data.URLModel}?${params.toString()}`);
			if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
			const body = await response.json();
			const known = new Set(appliedControls.map((control: any) => control.id));
			appliedControls = [
				...appliedControls,
				...(body.results ?? []).filter((row: any) => !known.has(row.id))
			];
			loadedFolders = new Set([...loadedFolders, ...folderIds]);
		} catch (error) {
			console.error('Error loading swimlanes:', error);
		} finally {
			const next = new Set(loadingFolders);
			for (const folderId of folderIds) next.delete(folderId);
			loadingFolders = next;
		}
	}

	function loadMore(folderId: string) {
		void loadFolderPage(folderId, loadedCountForFolder(folderId));
	}

	// View mode toggle
	let compactMode = $state(false);

	// Status columns configuration
	const statusColumns = [
		{
			id: '--',
			label: '--',
			color: 'bg-surface-200-800',
			borderColor: 'border-surface-300-700',
			cardAccent: 'border-l-surface-400-600',
			headerText: 'text-surface-600-400'
		},
		{
			id: 'to_do',
			label: m.toDo(),
			color: 'bg-blue-50 dark:bg-blue-950/40',
			borderColor: 'border-blue-300 dark:border-blue-800',
			cardAccent: 'border-l-blue-400',
			headerText: 'text-blue-700 dark:text-blue-300'
		},
		{
			id: 'in_progress',
			label: m.inProgress(),
			color: 'bg-violet-50 dark:bg-violet-950/40',
			borderColor: 'border-violet-300 dark:border-violet-800',
			cardAccent: 'border-l-violet-400',
			headerText: 'text-violet-700 dark:text-violet-300'
		},
		{
			id: 'on_hold',
			label: m.onHold(),
			color: 'bg-yellow-50 dark:bg-yellow-950/40',
			borderColor: 'border-yellow-300 dark:border-yellow-800',
			cardAccent: 'border-l-yellow-400',
			headerText: 'text-yellow-700 dark:text-yellow-300'
		},
		{
			id: 'active',
			label: m.active(),
			color: 'bg-green-50 dark:bg-green-950/40',
			borderColor: 'border-green-300 dark:border-green-800',
			cardAccent: 'border-l-green-400',
			headerText: 'text-green-700 dark:text-green-300'
		},
		{
			id: 'degraded',
			label: m.degraded(),
			color: 'bg-orange-50 dark:bg-orange-950/40',
			borderColor: 'border-orange-300 dark:border-orange-800',
			cardAccent: 'border-l-orange-400',
			headerText: 'text-orange-700 dark:text-orange-300'
		},
		{
			id: 'deprecated',
			label: m.deprecated(),
			color: 'bg-red-50 dark:bg-red-950/40',
			borderColor: 'border-red-300 dark:border-red-800',
			cardAccent: 'border-l-red-400',
			headerText: 'text-red-700 dark:text-red-300'
		}
	];

	// Priority display helper (API returns "P1", "P2", etc.)
	function getPriorityDisplay(priority: string | null): string {
		if (!priority || priority === '--') return '--';
		return priority;
	}

	// Priority color helper (API returns "P1", "P2", etc.)
	function getPriorityColor(priority: string | null): string {
		if (!priority || priority === '--') return 'bg-surface-200-800 text-surface-600-400';
		const colorMap: Record<string, string> = {
			P1: 'bg-red-100 text-red-800',
			P2: 'bg-orange-100 text-orange-800',
			P3: 'bg-yellow-100 text-yellow-800',
			P4: 'bg-green-100 text-green-800'
		};
		return colorMap[priority] || 'bg-surface-200-800 text-surface-600-400';
	}

	// Priority flag color helper
	function getPriorityFlagColor(priority: string | null): string {
		if (!priority || priority === '--') return 'text-surface-400-600';
		const colorMap: Record<string, string> = {
			P1: 'text-red-500',
			P2: 'text-orange-500',
			P3: 'text-yellow-500',
			P4: 'text-green-500'
		};
		return colorMap[priority] || 'text-surface-400-600';
	}

	// Effort display helper
	function getEffortDisplay(effort: string | null): string {
		if (!effort) return '--';
		return effort;
	}

	// Impact display helper
	function getImpactDisplay(impact: number | null): string {
		if (impact === null || impact === undefined) return '--';
		const impactMap: Record<number, string> = {
			1: m.veryLow(),
			2: m.low(),
			3: m.medium(),
			4: m.high(),
			5: m.veryHigh()
		};
		return impactMap[impact] || '--';
	}

	// Check if ETA is overdue
	function isOverdue(eta: string | null, status: string | null): boolean {
		if (!eta) return false;
		// Active and deprecated controls are not "overdue"
		if (status === 'active' || status === 'deprecated') return false;
		return new Date(eta) < new Date();
	}

	// Group controls by folder and status
	function getControlsForFolderAndStatus(folderId: string, statusId: string) {
		return appliedControls.filter((control: any) => {
			const controlFolderId = control.folder?.id || null;
			const controlStatus = control.status || '--';
			return controlFolderId === folderId && controlStatus === statusId;
		});
	}

	// Get count of controls per status column (across all folders)
	function getStatusCount(statusId: string): number {
		return Object.values(laneStats).reduce((sum, lane) => sum + (lane.perStatus[statusId] ?? 0), 0);
	}

	// Collapsible swimlanes: closed by default unless the whole board was
	// preloaded, since opening one is what fetches its cards.
	let collapsedFolders: Set<string> = $state(
		new Set(Object.keys(laneStats).filter((id) => !initiallyOpen.includes(id)))
	);

	function toggleFolder(folderId: string) {
		const next = new Set(collapsedFolders);
		if (next.has(folderId)) {
			next.delete(folderId);
			if (!loadedFolders.has(folderId)) void loadFolderPage(folderId, 0);
		} else {
			next.add(folderId);
		}
		collapsedFolders = next;
	}

	// Owner initials helper
	function getOwnerInitials(owner: any[] | null): { initials: string; name: string }[] {
		if (!owner || owner.length === 0) return [];
		return owner.map((o) => {
			const name = o.str || o.email || o.name || '?';
			const parts = name.split(/[\s@]+/);
			const initials =
				parts.length >= 2
					? (parts[0][0] + parts[1][0]).toUpperCase()
					: name.slice(0, 2).toUpperCase();
			return { initials, name };
		});
	}

	// Drag and drop state
	let draggedControl: any = $state(null);
	let dragOverStatus: string | null = $state(null);
	let dragOverFolder: string | null = $state(null);
	// Counter per drop zone to prevent flickering from child enter/leave events
	let dragEnterCounters: Map<string, number> = $state(new Map());

	function dropZoneKey(statusId: string, folderId: string): string {
		return `${statusId}::${folderId}`;
	}

	function shiftLaneCount(folderId: string | null, fromStatus: string, toStatus: string) {
		const lane = folderId ? laneStats[folderId] : undefined;
		if (!lane || fromStatus === toStatus) return;
		lane.perStatus[fromStatus] = Math.max(0, (lane.perStatus[fromStatus] ?? 0) - 1);
		lane.perStatus[toStatus] = (lane.perStatus[toStatus] ?? 0) + 1;
	}

	function handleDragStart(event: DragEvent, control: any) {
		draggedControl = control;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.setData('text/plain', control.id);
		}
	}

	function handleDragEnter(event: DragEvent, statusId: string, folderId: string) {
		event.preventDefault();
		const key = dropZoneKey(statusId, folderId);
		const count = (dragEnterCounters.get(key) || 0) + 1;
		dragEnterCounters = new Map(dragEnterCounters).set(key, count);
		dragOverStatus = statusId;
		dragOverFolder = folderId;
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
	}

	function handleDragLeave(_event: DragEvent, statusId: string, folderId: string) {
		const key = dropZoneKey(statusId, folderId);
		const count = (dragEnterCounters.get(key) || 0) - 1;
		const next = new Map(dragEnterCounters);
		if (count <= 0) {
			next.delete(key);
			// Only clear highlight if leaving the currently highlighted zone
			if (dragOverStatus === statusId && dragOverFolder === folderId) {
				dragOverStatus = null;
				dragOverFolder = null;
			}
		} else {
			next.set(key, count);
		}
		dragEnterCounters = next;
	}

	function handleDragEnd() {
		draggedControl = null;
		dragOverStatus = null;
		dragOverFolder = null;
		dragEnterCounters = new Map();
	}

	async function handleDrop(event: DragEvent, statusId: string) {
		event.preventDefault();
		if (!draggedControl) return;

		// Only update if status actually changed
		const currentStatus = draggedControl.status || '--';
		if (currentStatus === statusId) {
			handleDragEnd();
			return;
		}

		// Store the control info before clearing draggedControl
		const controlToUpdate = draggedControl;

		// Optimistically update local state first for better UX
		const controlIndex = appliedControls.findIndex((c: any) => c.id === controlToUpdate.id);
		const previousStatus = controlIndex !== -1 ? appliedControls[controlIndex].status : null;
		const laneId = controlToUpdate.folder?.id ?? null;

		if (controlIndex !== -1) {
			// Update status and create new array reference to trigger reactivity
			appliedControls[controlIndex] = { ...appliedControls[controlIndex], status: statusId };
			// The headers read the aggregate, so move the card there too.
			shiftLaneCount(laneId, currentStatus, statusId);
		}

		try {
			const response = await fetch('?/updateAppliedControl', {
				method: 'POST',
				body: JSON.stringify({
					id: controlToUpdate.id,
					status: statusId
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}
		} catch (error) {
			console.error('Error updating control status:', error);
			if (controlIndex !== -1 && previousStatus !== null) {
				appliedControls[controlIndex] = {
					...appliedControls[controlIndex],
					status: previousStatus
				};
				shiftLaneCount(laneId, statusId, previousStatus || '--');
			}
		}

		handleDragEnd();
	}

	// Format date for display
	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '--';
		return formatDateOrDateTime(dateStr, getLocale());
	}
</script>

<div class="flex flex-col h-full min-h-screen bg-surface-100-900 p-4">
	<!-- Header -->
	<div class="flex justify-between items-center mb-4">
		<a
			href={data.backUrl}
			class="flex items-center space-x-2 text-primary-800-200 hover:text-primary-600-400"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<span>{safeTranslate(data.backLabel)}</span>
		</a>
		<div class="flex items-center space-x-4">
			<span class="text-sm text-surface-600-400">
				{totalCount}
				{m.appliedControls().toLowerCase()}
			</span>
			<button
				type="button"
				class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors
					{compactMode
					? 'bg-primary-100 border-primary-300 text-primary-700'
					: 'bg-surface-50-950 border-surface-300-700 text-surface-600-400 hover:bg-surface-100-900'}"
				onclick={() => (compactMode = !compactMode)}
				title={compactMode ? m.detailedView() : m.compactView()}
			>
				<i class="fa-solid {compactMode ? 'fa-expand' : 'fa-compress'} text-xs"></i>
				<span>{compactMode ? m.detailedView() : m.compactView()}</span>
			</button>
		</div>
	</div>

	<!-- Kanban Board -->
	<div class="flex-1 overflow-auto">
		<div class="min-w-max">
			<!-- Column Headers -->
			<div class="flex sticky top-0 z-10 bg-surface-100-900 pb-2">
				<div class="w-48 flex-shrink-0 px-2">
					<!-- Folder column header -->
					<div class="h-10 flex items-center font-semibold text-surface-700-300">
						<i class="fa-solid fa-folder mr-2"></i>
						{m.domain()}
					</div>
				</div>
				{#each statusColumns as column}
					{@const count = getStatusCount(column.id)}
					<div class="w-64 flex-shrink-0 px-2">
						<div
							class="h-10 flex items-center justify-center gap-2 font-semibold rounded-t-lg {column.color} border-t-2 {column.borderColor} {column.headerText}"
						>
							<span>{column.label}</span>
							<span
								class="inline-flex items-center justify-center min-w-5 h-5 px-1.5 text-xs font-bold rounded-full bg-surface-50-950/70"
							>
								{count}
							</span>
						</div>
					</div>
				{/each}
			</div>

			<!-- Swimlanes (Folders) -->
			{#each swimlanes as lane}
				{@const folder = lane.folder}
				{@const isCollapsed = collapsedFolders.has(folder.id)}
				{@const folderCount = lane.count}
				<div class="mb-2 border-b border-surface-200-800 pb-2">
					<!-- Folder Header Row (clickable to collapse) -->
					<div class="flex">
						<div class="w-48 flex-shrink-0 px-2">
							<button
								type="button"
								class="w-full flex items-center gap-2 py-2 font-medium text-surface-700-300 hover:text-surface-900-100 text-left group"
								onclick={() => toggleFolder(folder.id)}
							>
								<i
									class="fa-solid fa-chevron-right text-xs text-surface-400-600 group-hover:text-surface-600-400 transition-transform {isCollapsed
										? ''
										: 'rotate-90'}"
								></i>
								<span class="truncate" title={folder.str || folder.name}>
									{folder.str || folder.name}
								</span>
								<span class="text-xs text-surface-400-600 font-normal flex-shrink-0">
									{folderCount}
								</span>
							</button>
						</div>

						{#if isCollapsed}
							<!-- Collapsed summary: real counts, no cards fetched yet -->
							{#each statusColumns as column}
								{@const count = lane.perStatus[column.id] ?? 0}
								<div class="w-64 flex-shrink-0 px-2 flex items-center justify-center">
									{#if count > 0}
										<span class="text-xs font-medium {column.headerText}">
											{count}
										</span>
									{/if}
								</div>
							{/each}
						{/if}
					</div>

					<!-- Expanded content -->
					{#if !isCollapsed}
						<div class="flex">
							<div class="w-48 flex-shrink-0 px-2"></div>
							<!-- Status Columns for this Folder -->
							{#each statusColumns as column}
								{@const controls = getControlsForFolderAndStatus(folder.id, column.id)}
								{@const cellTotal = lane.perStatus[column.id] ?? 0}
								{@const hiddenInCell = Math.max(0, cellTotal - controls.length)}
								<div
									class="w-64 flex-shrink-0 px-2"
									ondragenter={(e) => handleDragEnter(e, column.id, folder.id)}
									ondragover={handleDragOver}
									ondragleave={(e) => handleDragLeave(e, column.id, folder.id)}
									ondrop={(e) => handleDrop(e, column.id)}
									role="region"
									aria-label="{column.label} column for {folder.str || folder.name}"
								>
									<div
										class="min-h-24 rounded-lg p-2 transition-all {column.color} {dragOverStatus ===
											column.id && dragOverFolder === folder.id
											? 'ring-2 ring-primary-500 ring-offset-2'
											: ''}"
									>
										<!-- Drop placeholder when dragging -->
										{#if draggedControl && dragOverStatus === column.id && dragOverFolder === folder.id}
											<div
												class="border-2 border-dashed border-primary-300 rounded-lg p-3 mb-2 bg-primary-50/50 flex items-center justify-center"
											>
												<span class="text-xs text-primary-500 font-medium"
													>{m.dropHereToChangeStatus()}</span
												>
											</div>
										{/if}

										{#if loadingFolders.has(folder.id) && controls.length === 0}
											<div class="text-center py-4">
												<i class="fa-solid fa-spinner fa-spin text-surface-400-600"></i>
											</div>
										{:else if controls.length === 0 && !(draggedControl && dragOverStatus === column.id && dragOverFolder === folder.id)}
											<div class="text-xs text-surface-400-600 text-center py-4 italic">
												{#if hiddenInCell > 0}
													+{hiddenInCell}
												{:else}
													{m.noControlsInCategory()}
												{/if}
											</div>
										{:else}
											<div class={compactMode ? 'space-y-1' : 'space-y-2'}>
												{#each controls as control (control.id)}
													{@const overdue = isOverdue(control.eta, control.status)}
													{#if compactMode}
														<!-- Compact card -->
														<div
															class="bg-surface-50-950 rounded px-2 py-1.5 cursor-move hover:shadow-sm transition-all border border-surface-200-800 border-l-[3px] {column.cardAccent} {draggedControl?.id ===
															control.id
																? 'opacity-40 scale-95'
																: ''} {overdue ? 'ring-1 ring-red-300' : ''}"
															draggable="true"
															ondragstart={(e) => handleDragStart(e, control)}
															ondragend={handleDragEnd}
															role="article"
															aria-label={control.name}
														>
															<div class="flex items-center gap-2">
																{#if control.priority}
																	<span
																		class="flex-shrink-0 w-6 text-center text-[10px] font-bold {getPriorityFlagColor(
																			control.priority
																		)}"
																	>
																		{getPriorityDisplay(control.priority)}
																	</span>
																{/if}
																<a
																	href="/applied-controls/{control.id}"
																	class="text-xs text-surface-900-100 hover:text-primary-600 truncate flex-1"
																	title={control.name}
																>
																	{#if control.ref_id}<span
																			class="font-mono text-surface-400-600 mr-1"
																			>{control.ref_id}</span
																		>{/if}{control.name || 'Unnamed Control'}
																</a>
																{#if overdue}
																	<i
																		class="fa-solid fa-triangle-exclamation text-red-500 text-[10px] flex-shrink-0"
																	></i>
																{/if}
																{#if control.progress_field !== null && control.progress_field !== undefined}
																	<div
																		class="flex-shrink-0 w-10 bg-surface-200-800 rounded-full h-1.5"
																	>
																		<div
																			class="h-1.5 rounded-full {control.progress_field >= 100
																				? 'bg-green-500'
																				: control.progress_field >= 50
																					? 'bg-yellow-500'
																					: 'bg-blue-500'}"
																			style="width: {Math.min(control.progress_field, 100)}%"
																		></div>
																	</div>
																{/if}
																{#if control.owner && control.owner.length > 0}
																	<div class="flex -space-x-1 flex-shrink-0">
																		{#each getOwnerInitials(control.owner).slice(0, 2) as owner}
																			<span
																				class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-surface-200-800 text-surface-600-400 text-[9px] font-medium ring-1 ring-surface-50-950"
																				title={owner.name}
																			>
																				{owner.initials}
																			</span>
																		{/each}
																	</div>
																{/if}
															</div>
														</div>
													{:else}
														<!-- Detailed card -->
														<div
															class="bg-surface-50-950 rounded-lg shadow-sm p-3 cursor-move hover:shadow-md transition-all border border-surface-200-800 border-l-[3px] {column.cardAccent} {draggedControl?.id ===
															control.id
																? 'opacity-40 scale-95'
																: ''} {overdue ? 'ring-1 ring-red-300' : ''}"
															draggable="true"
															ondragstart={(e) => handleDragStart(e, control)}
															ondragend={handleDragEnd}
															role="article"
															aria-label={control.name}
														>
															<!-- Card Header -->
															<div class="flex items-start justify-between gap-2 mb-2">
																<div class="min-w-0">
																	{#if control.ref_id}
																		<span class="text-[10px] font-mono text-surface-400-600"
																			>{control.ref_id}</span
																		>
																	{/if}
																	<a
																		href="/applied-controls/{control.id}"
																		class="font-medium text-sm text-surface-900-100 hover:text-primary-600 line-clamp-2 block"
																		title={control.name}
																	>
																		{control.name || 'Unnamed Control'}
																	</a>
																</div>
																{#if control.priority}
																	<span
																		class="flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold {getPriorityColor(
																			control.priority
																		)}"
																	>
																		{getPriorityDisplay(control.priority)}
																	</span>
																{/if}
															</div>

															<!-- Card Details -->
															<div class="space-y-1.5 text-xs text-surface-600-400">
																<!-- Progress Bar -->
																{#if control.progress_field !== null && control.progress_field !== undefined}
																	<div class="flex flex-col space-y-1">
																		<div class="flex items-center justify-between">
																			<span>{m.progress()}</span>
																			<span class="font-medium">{control.progress_field}%</span>
																		</div>
																		<div class="w-full bg-surface-200-800 rounded-full h-1.5">
																			<div
																				class="h-1.5 rounded-full transition-all {control.progress_field >=
																				100
																					? 'bg-green-500'
																					: control.progress_field >= 50
																						? 'bg-yellow-500'
																						: 'bg-blue-500'}"
																				style="width: {Math.min(control.progress_field, 100)}%"
																			></div>
																		</div>
																	</div>
																{/if}

																<!-- ETA -->
																{#if control.eta}
																	<div
																		class="flex items-center space-x-2 {overdue
																			? 'text-red-600 font-medium'
																			: ''}"
																	>
																		<i
																			class="fa-solid {overdue
																				? 'fa-triangle-exclamation'
																				: 'fa-calendar'} w-4 text-center"
																		></i>
																		<span>{formatDate(control.eta)}</span>
																		{#if overdue}
																			<span class="text-[10px] uppercase tracking-wide"
																				>{m.overdue()}</span
																			>
																		{/if}
																	</div>
																{/if}

																<!-- Category / CSF function chips -->
																{#if control.category || control.csf_function}
																	<div class="flex flex-wrap gap-1">
																		{#if control.csf_function}
																			<span
																				class="px-1.5 py-0.5 bg-surface-100-900 text-surface-600-400 rounded text-[10px]"
																			>
																				{control.csf_function}
																			</span>
																		{/if}
																		{#if control.category}
																			<span
																				class="px-1.5 py-0.5 bg-surface-100-900 text-surface-600-400 rounded text-[10px]"
																			>
																				{control.category}
																			</span>
																		{/if}
																	</div>
																{/if}

																<!-- Footer: owners + effort/impact -->
																<div class="flex items-center justify-between pt-1">
																	<!-- Owner initials -->
																	<div class="flex -space-x-1">
																		{#each getOwnerInitials(control.owner) as owner}
																			<span
																				class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-surface-200-800 text-surface-600-400 text-[10px] font-medium ring-1 ring-surface-50-950"
																				title={owner.name}
																			>
																				{owner.initials}
																			</span>
																		{/each}
																	</div>
																	<!-- Effort / Impact -->
																	<div class="flex items-center gap-1.5">
																		{#if control.control_impact}
																			<span
																				class="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300 rounded text-[10px]"
																				title={m.controlImpact()}
																			>
																				{getImpactDisplay(control.control_impact)}
																			</span>
																		{/if}
																		{#if control.effort}
																			<span
																				class="px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 rounded text-[10px]"
																				title={m.effort()}
																			>
																				{getEffortDisplay(control.effort)}
																			</span>
																		{/if}
																	</div>
																</div>
															</div>
														</div>
													{/if}
												{/each}
												{#if hiddenInCell > 0}
													<p class="text-xs text-surface-400-600 text-center italic pt-1">
														+{hiddenInCell}
													</p>
												{/if}
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
						{#if loadedFolders.has(folder.id) && loadedCountForFolder(folder.id) < lane.count}
							<div class="flex pl-48">
								<button
									type="button"
									class="btn preset-tonal-surface text-xs my-1"
									disabled={loadingFolders.has(folder.id)}
									onclick={() => loadMore(folder.id)}
								>
									{#if loadingFolders.has(folder.id)}
										<i class="fa-solid fa-spinner fa-spin mr-2"></i>
									{/if}
									{loadedCountForFolder(folder.id)} / {lane.count}
								</button>
							</div>
						{/if}
					{/if}
				</div>
			{/each}

			<!-- Empty state if no folders -->
			{#if swimlanes.length === 0}
				<div class="flex items-center justify-center py-12 text-surface-600-400">
					<div class="text-center">
						<i class="fa-solid fa-folder-open text-4xl mb-4 text-surface-300-700"></i>
						<p>{m.noControlsInCategory()}</p>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
