<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Create local mutable copy of applied controls to avoid SvelteKit data reload issues
	let appliedControls = $state([...data.applied_controls]);

	// View mode toggle
	let compactMode = $state(false);

	// Status columns configuration
	const statusColumns = [
		{
			id: '--',
			label: '--',
			color: 'bg-gray-100',
			borderColor: 'border-gray-300',
			cardAccent: 'border-l-gray-400',
			headerText: 'text-gray-600'
		},
		{
			id: 'to_do',
			label: m.toDo(),
			color: 'bg-blue-50',
			borderColor: 'border-blue-300',
			cardAccent: 'border-l-blue-400',
			headerText: 'text-blue-700'
		},
		{
			id: 'in_progress',
			label: m.inProgress(),
			color: 'bg-violet-50',
			borderColor: 'border-violet-300',
			cardAccent: 'border-l-violet-400',
			headerText: 'text-violet-700'
		},
		{
			id: 'on_hold',
			label: m.onHold(),
			color: 'bg-yellow-50',
			borderColor: 'border-yellow-300',
			cardAccent: 'border-l-yellow-400',
			headerText: 'text-yellow-700'
		},
		{
			id: 'active',
			label: m.active(),
			color: 'bg-green-50',
			borderColor: 'border-green-300',
			cardAccent: 'border-l-green-400',
			headerText: 'text-green-700'
		},
		{
			id: 'degraded',
			label: m.degraded(),
			color: 'bg-orange-50',
			borderColor: 'border-orange-300',
			cardAccent: 'border-l-orange-400',
			headerText: 'text-orange-700'
		},
		{
			id: 'deprecated',
			label: m.deprecated(),
			color: 'bg-red-50',
			borderColor: 'border-red-300',
			cardAccent: 'border-l-red-400',
			headerText: 'text-red-700'
		}
	];

	// Priority display helper (API returns "P1", "P2", etc.)
	function getPriorityDisplay(priority: string | null): string {
		if (!priority || priority === '--') return '--';
		return priority;
	}

	// Priority color helper (API returns "P1", "P2", etc.)
	function getPriorityColor(priority: string | null): string {
		if (!priority || priority === '--') return 'bg-gray-100 text-gray-600';
		const colorMap: Record<string, string> = {
			P1: 'bg-red-100 text-red-800',
			P2: 'bg-orange-100 text-orange-800',
			P3: 'bg-yellow-100 text-yellow-800',
			P4: 'bg-green-100 text-green-800'
		};
		return colorMap[priority] || 'bg-gray-100 text-gray-600';
	}

	// Priority flag color helper
	function getPriorityFlagColor(priority: string | null): string {
		if (!priority || priority === '--') return 'text-gray-400';
		const colorMap: Record<string, string> = {
			P1: 'text-red-500',
			P2: 'text-orange-500',
			P3: 'text-yellow-500',
			P4: 'text-green-500'
		};
		return colorMap[priority] || 'text-gray-400';
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
		return appliedControls.filter((control: any) => {
			const controlStatus = control.status || '--';
			return controlStatus === statusId;
		}).length;
	}

	// Get unique folders from applied controls
	function getUniqueFolders() {
		const folderMap = new Map();
		appliedControls.forEach((control: any) => {
			if (control.folder) {
				folderMap.set(control.folder.id, control.folder);
			}
		});
		return Array.from(folderMap.values());
	}

	// Collapsible swimlanes
	let collapsedFolders: Set<string> = $state(new Set());

	function toggleFolder(folderId: string) {
		const next = new Set(collapsedFolders);
		if (next.has(folderId)) {
			next.delete(folderId);
		} else {
			next.add(folderId);
		}
		collapsedFolders = next;
	}

	// Get count of controls in a folder
	function getFolderControlCount(folderId: string): number {
		return appliedControls.filter((control: any) => control.folder?.id === folderId).length;
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

		if (controlIndex !== -1) {
			// Update status and create new array reference to trigger reactivity
			appliedControls[controlIndex] = { ...appliedControls[controlIndex], status: statusId };
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
			}
		}

		handleDragEnd();
	}

	// Format date for display
	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '--';
		const date = new Date(dateStr);
		return date.toLocaleDateString();
	}

	const folders = $derived(getUniqueFolders());
</script>

<div class="flex flex-col h-full min-h-screen bg-gray-50 p-4">
	<!-- Header -->
	<div class="flex justify-between items-center mb-4">
		<a
			href={data.backUrl}
			class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<span>{data.backLabel}</span>
		</a>
		<div class="flex items-center space-x-4">
			<span class="text-sm text-gray-600">
				{appliedControls.length}
				{m.appliedControls().toLowerCase()}
			</span>
			<button
				type="button"
				class="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors
					{compactMode
					? 'bg-primary-100 border-primary-300 text-primary-700'
					: 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'}"
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
			<div class="flex sticky top-0 z-10 bg-gray-50 pb-2">
				<div class="w-48 flex-shrink-0 px-2">
					<!-- Folder column header -->
					<div class="h-10 flex items-center font-semibold text-gray-700">
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
								class="inline-flex items-center justify-center min-w-5 h-5 px-1.5 text-xs font-bold rounded-full bg-white/70"
							>
								{count}
							</span>
						</div>
					</div>
				{/each}
			</div>

			<!-- Swimlanes (Folders) -->
			{#each folders as folder}
				{@const isCollapsed = collapsedFolders.has(folder.id)}
				{@const folderCount = getFolderControlCount(folder.id)}
				<div class="mb-2 border-b border-gray-200 pb-2">
					<!-- Folder Header Row (clickable to collapse) -->
					<div class="flex">
						<div class="w-48 flex-shrink-0 px-2">
							<button
								type="button"
								class="w-full flex items-center gap-2 py-2 font-medium text-gray-700 hover:text-gray-900 text-left group"
								onclick={() => toggleFolder(folder.id)}
							>
								<i
									class="fa-solid fa-chevron-right text-xs text-gray-400 group-hover:text-gray-600 transition-transform {isCollapsed
										? ''
										: 'rotate-90'}"
								></i>
								<span class="truncate" title={folder.str || folder.name}>
									{folder.str || folder.name}
								</span>
								<span class="text-xs text-gray-400 font-normal flex-shrink-0">
									{folderCount}
								</span>
							</button>
						</div>

						{#if isCollapsed}
							<!-- Collapsed summary: show count per status -->
							{#each statusColumns as column}
								{@const controls = getControlsForFolderAndStatus(folder.id, column.id)}
								<div class="w-64 flex-shrink-0 px-2 flex items-center justify-center">
									{#if controls.length > 0}
										<span class="text-xs font-medium {column.headerText}">
											{controls.length}
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

										{#if controls.length === 0 && !(draggedControl && dragOverStatus === column.id && dragOverFolder === folder.id)}
											<div class="text-xs text-gray-400 text-center py-4 italic">
												{m.noControlsInCategory()}
											</div>
										{:else}
											<div class={compactMode ? 'space-y-1' : 'space-y-2'}>
												{#each controls as control (control.id)}
													{@const overdue = isOverdue(control.eta, control.status)}
													{#if compactMode}
														<!-- Compact card -->
														<div
															class="bg-white rounded px-2 py-1.5 cursor-move hover:shadow-sm transition-all border border-gray-200 border-l-[3px] {column.cardAccent} {draggedControl?.id ===
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
																	class="text-xs text-gray-900 hover:text-primary-600 truncate flex-1"
																	title={control.name}
																>
																	{#if control.ref_id}<span class="font-mono text-gray-400 mr-1"
																			>{control.ref_id}</span
																		>{/if}{control.name || 'Unnamed Control'}
																</a>
																{#if overdue}
																	<i
																		class="fa-solid fa-triangle-exclamation text-red-500 text-[10px] flex-shrink-0"
																	></i>
																{/if}
																{#if control.progress_field !== null && control.progress_field !== undefined}
																	<div class="flex-shrink-0 w-10 bg-gray-200 rounded-full h-1.5">
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
																				class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-[9px] font-medium ring-1 ring-white"
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
															class="bg-white rounded-lg shadow-sm p-3 cursor-move hover:shadow-md transition-all border border-gray-200 border-l-[3px] {column.cardAccent} {draggedControl?.id ===
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
																		<span class="text-[10px] font-mono text-gray-400"
																			>{control.ref_id}</span
																		>
																	{/if}
																	<a
																		href="/applied-controls/{control.id}"
																		class="font-medium text-sm text-gray-900 hover:text-primary-600 line-clamp-2 block"
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
															<div class="space-y-1.5 text-xs text-gray-600">
																<!-- Progress Bar -->
																{#if control.progress_field !== null && control.progress_field !== undefined}
																	<div class="flex flex-col space-y-1">
																		<div class="flex items-center justify-between">
																			<span>{m.progress()}</span>
																			<span class="font-medium">{control.progress_field}%</span>
																		</div>
																		<div class="w-full bg-gray-200 rounded-full h-1.5">
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
																				class="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px]"
																			>
																				{control.csf_function}
																			</span>
																		{/if}
																		{#if control.category}
																			<span
																				class="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px]"
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
																				class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-200 text-gray-600 text-[10px] font-medium ring-1 ring-white"
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
																				class="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-[10px]"
																				title={m.controlImpact()}
																			>
																				{getImpactDisplay(control.control_impact)}
																			</span>
																		{/if}
																		{#if control.effort}
																			<span
																				class="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded text-[10px]"
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
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/each}

			<!-- Empty state if no folders -->
			{#if folders.length === 0}
				<div class="flex items-center justify-center py-12 text-gray-500">
					<div class="text-center">
						<i class="fa-solid fa-folder-open text-4xl mb-4 text-gray-300"></i>
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
