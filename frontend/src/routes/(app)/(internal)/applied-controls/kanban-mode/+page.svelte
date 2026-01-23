<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Create local mutable copy of applied controls to avoid SvelteKit data reload issues
	let appliedControls = $state([...data.applied_controls]);

	// Status columns configuration
	const statusColumns = [
		{ id: '--', label: '--', color: 'bg-gray-100', borderColor: 'border-gray-300' },
		{ id: 'to_do', label: m.toDo(), color: 'bg-blue-50', borderColor: 'border-blue-300' },
		{
			id: 'in_progress',
			label: m.inProgress(),
			color: 'bg-yellow-50',
			borderColor: 'border-yellow-300'
		},
		{ id: 'on_hold', label: m.onHold(), color: 'bg-orange-50', borderColor: 'border-orange-300' },
		{ id: 'active', label: m.active(), color: 'bg-green-50', borderColor: 'border-green-300' },
		{
			id: 'deprecated',
			label: m.deprecated(),
			color: 'bg-red-50',
			borderColor: 'border-red-300'
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

	// Group controls by folder and status
	function getControlsForFolderAndStatus(folderId: string, statusId: string) {
		return appliedControls.filter((control: any) => {
			const controlFolderId = control.folder?.id || null;
			const controlStatus = control.status || '--';
			return controlFolderId === folderId && controlStatus === statusId;
		});
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

	// Drag and drop state
	let draggedControl: any = $state(null);
	let dragOverStatus: string | null = $state(null);
	let dragOverFolder: string | null = $state(null);

	function handleDragStart(event: DragEvent, control: any) {
		draggedControl = control;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
			event.dataTransfer.setData('text/plain', control.id);
		}
	}

	function handleDragOver(event: DragEvent, statusId: string, folderId: string) {
		event.preventDefault();
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = 'move';
		}
		dragOverStatus = statusId;
		dragOverFolder = folderId;
	}

	function handleDragLeave() {
		dragOverStatus = null;
		dragOverFolder = null;
	}

	function handleDragEnd() {
		draggedControl = null;
		dragOverStatus = null;
		dragOverFolder = null;
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

	// Get owner display
	function getOwnerDisplay(owner: any[] | null): string {
		if (!owner || owner.length === 0) return '--';
		return owner.map((o) => o.str || o.email || o.name).join(', ');
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
					<div class="w-64 flex-shrink-0 px-2">
						<div
							class="h-10 flex items-center justify-center font-semibold rounded-t-lg {column.color} border-t-2 {column.borderColor}"
						>
							{column.label}
						</div>
					</div>
				{/each}
			</div>

			<!-- Swimlanes (Folders) -->
			{#each folders as folder}
				<div class="flex mb-2 border-b border-gray-200 pb-2">
					<!-- Folder Name -->
					<div class="w-48 flex-shrink-0 px-2">
						<div
							class="h-full min-h-24 flex items-start pt-2 font-medium text-gray-700 sticky left-0 bg-gray-50"
						>
							<span class="truncate" title={folder.str || folder.name}>
								{folder.str || folder.name}
							</span>
						</div>
					</div>

					<!-- Status Columns for this Folder -->
					{#each statusColumns as column}
						{@const controls = getControlsForFolderAndStatus(folder.id, column.id)}
						<div
							class="w-64 flex-shrink-0 px-2"
							ondragover={(e) => handleDragOver(e, column.id, folder.id)}
							ondragleave={handleDragLeave}
							ondrop={(e) => handleDrop(e, column.id)}
							role="region"
							aria-label="{column.label} column for {folder.str || folder.name}"
						>
							<div
								class="min-h-24 rounded-lg p-2 transition-colors {column.color} {dragOverStatus ===
									column.id && dragOverFolder === folder.id
									? 'ring-2 ring-primary-500 ring-offset-2'
									: ''}"
							>
								{#if controls.length === 0}
									<div class="text-xs text-gray-400 text-center py-4 italic">
										{m.noControlsInCategory()}
									</div>
								{:else}
									<div class="space-y-2">
										{#each controls as control (control.id)}
											<div
												class="bg-white rounded-lg shadow-sm p-3 cursor-move hover:shadow-md transition-shadow border border-gray-200 {draggedControl?.id ===
												control.id
													? 'opacity-50'
													: ''}"
												draggable="true"
												ondragstart={(e) => handleDragStart(e, control)}
												ondragend={handleDragEnd}
												role="article"
												aria-label={control.name}
											>
												<!-- Card Header -->
												<div class="mb-2">
													<a
														href="/applied-controls/{control.id}"
														class="font-medium text-sm text-gray-900 hover:text-primary-600 line-clamp-2"
														title={control.name}
													>
														{control.name || 'Unnamed Control'}
													</a>
												</div>

												<!-- Card Details -->
												<div class="space-y-1 text-xs text-gray-600">
													<!-- Progress Bar -->
													{#if control.progress_field !== null && control.progress_field !== undefined}
														<div class="flex flex-col space-y-1">
															<div class="flex items-center justify-between">
																<span>{m.progress()}</span>
																<span class="font-medium">{control.progress_field}%</span>
															</div>
															<div class="w-full bg-gray-200 rounded-full h-2">
																<div
																	class="h-2 rounded-full transition-all {control.progress_field >=
																	100
																		? 'bg-green-500'
																		: control.progress_field >= 50
																			? 'bg-yellow-500'
																			: 'bg-blue-500'}"
																	style="width: {control.progress_field}%"
																></div>
															</div>
														</div>
													{/if}

													<!-- Priority -->
													{#if control.priority}
														<div class="flex items-center space-x-2">
															<i
																class="fa-solid fa-flag w-4 text-center {getPriorityFlagColor(
																	control.priority
																)}"
															></i>
															<span
																class="px-1.5 py-0.5 rounded {getPriorityColor(control.priority)}"
															>
																{getPriorityDisplay(control.priority)}
															</span>
														</div>
													{/if}

													<!-- ETA -->
													{#if control.eta}
														<div class="flex items-center space-x-2">
															<i class="fa-solid fa-calendar w-4 text-center"></i>
															<span>{formatDate(control.eta)}</span>
														</div>
													{/if}

													<!-- Owner/Assignee -->
													{#if control.owner && control.owner.length > 0}
														<div class="flex items-center space-x-2">
															<i class="fa-solid fa-user w-4 text-center"></i>
															<span class="truncate" title={getOwnerDisplay(control.owner)}>
																{getOwnerDisplay(control.owner)}
															</span>
														</div>
													{/if}

													<!-- Impact & Effort -->
													<div class="flex items-center space-x-3 pt-1">
														{#if control.control_impact}
															<span
																class="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-xs"
																title={m.controlImpact()}
															>
																{getImpactDisplay(control.control_impact)}
															</span>
														{/if}
														{#if control.effort}
															<span
																class="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs"
																title={m.effort()}
															>
																{getEffortDisplay(control.effort)}
															</span>
														{/if}
													</div>
												</div>
											</div>
										{/each}
									</div>
								{/if}
							</div>
						</div>
					{/each}
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
