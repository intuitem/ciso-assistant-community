<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { goto } from '$app/navigation';
	import { navigating } from '$app/stores';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set(m.yearlyTasksReview());

	// View settings
	let compactMode = $state(false);

	// Function to get translated short month names
	function getMonthName(monthIndex: number): string {
		const monthNames = [
			m.januaryShort(),
			m.februaryShort(),
			m.marchShort(),
			m.aprilShort(),
			m.mayShort(),
			m.juneShort(),
			m.julyShort(),
			m.augustShort(),
			m.septemberShort(),
			m.octoberShort(),
			m.novemberShort(),
			m.decemberShort()
		];
		return monthNames[monthIndex];
	}

	// Convert month/year to YYYY-MM format for month input
	function toMonthFormat(year: number, month: number): string {
		return `${year}-${String(month).padStart(2, '0')}`;
	}

	// Parse YYYY-MM format to month and year
	function parseMonthFormat(value: string): { year: number; month: number } {
		const [year, month] = value.split('-').map(Number);
		return { year, month };
	}

	// Get bucket label — for monthly, use translated month name
	function getBucketLabel(bucket: { key: string; label: string }): string {
		if (data.granularity === 'monthly') {
			const parts = bucket.key.split('-');
			const monthIndex = parseInt(parts[1]) - 1;
			return getMonthName(monthIndex);
		}
		return bucket.label;
	}

	let startPeriod = $state(toMonthFormat(data.startYear, data.startMonth));
	let endPeriod = $state(toMonthFormat(data.endYear, data.endMonth));
	let selectedFolder = $state(data.selectedFolder);
	let selectedGranularity = $state(data.granularity || 'monthly');
	let selectedAssignedTo = $state(data.selectedAssignedTo || '');
	let selectedAppliedControls = $state(data.selectedAppliedControls || '');
	let selectedStatus = $state(data.selectedStatus || '');

	// Derived values for display
	let startFormatted = $derived.by(() => {
		const { year, month } = parseMonthFormat(startPeriod);
		return { year, month, label: getMonthName(month - 1) };
	});

	let endFormatted = $derived.by(() => {
		const { year, month } = parseMonthFormat(endPeriod);
		return { year, month, label: getMonthName(month - 1) };
	});

	function getStatusColor(status: string | null): string {
		if (!status) return 'bg-white';
		if (status === 'completed') return 'bg-green-200';
		if (status === 'in_progress') return 'bg-orange-200';
		if (status === 'pending') return 'bg-red-200';
		if (status === 'cancelled') return 'bg-gray-200';
		return 'bg-white';
	}

	function applyFilters() {
		const start = parseMonthFormat(startPeriod);
		const end = parseMonthFormat(endPeriod);
		const params = new URLSearchParams();
		params.set('start_month', start.month.toString());
		params.set('start_year', start.year.toString());
		params.set('end_month', end.month.toString());
		params.set('end_year', end.year.toString());
		params.set('granularity', selectedGranularity);
		if (selectedFolder) params.set('folder', selectedFolder);
		if (selectedAssignedTo) params.set('assigned_to', selectedAssignedTo);
		if (selectedAppliedControls) params.set('applied_controls', selectedAppliedControls);
		if (selectedStatus) params.set('status', selectedStatus);
		goto(`/experimental/yearly-tasks-review?${params.toString()}`);
	}

	function resetFilters() {
		const currentYear = new Date().getFullYear();
		startPeriod = toMonthFormat(currentYear, 1);
		endPeriod = toMonthFormat(currentYear, 12);
		selectedFolder = '';
		selectedGranularity = 'monthly';
		selectedAssignedTo = '';
		selectedAppliedControls = '';
		selectedStatus = '';
		goto('/experimental/yearly-tasks-review');
	}
</script>

<div class="bg-white p-8 space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold mb-2">
				{m.yearlyTasksReview()}
			</h1>
			<p class="text-gray-600">
				{startFormatted.label}
				{startFormatted.year}
				{m.periodTo()}
				{endFormatted.label}
				{endFormatted.year}
				{#if data.granularity === 'weekly'}
					<span class="ml-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full"
						>{m.weekly()}</span
					>
				{/if}
			</p>
		</div>
		<!-- Compact mode toggle -->
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

	<!-- Filters -->
	<div class="bg-gray-50 p-4 rounded-lg border">
		<div class="flex gap-4 items-end flex-wrap">
			<!-- Start Period -->
			<div class="min-w-[140px]">
				<label for="start-period-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.startPeriod()}
				</label>
				<input
					id="start-period-filter"
					type="month"
					bind:value={startPeriod}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
			</div>

			<!-- End Period -->
			<div class="min-w-[140px]">
				<label for="end-period-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.endPeriod()}
				</label>
				<input
					id="end-period-filter"
					type="month"
					bind:value={endPeriod}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
			</div>

			<!-- Granularity -->
			<div class="min-w-[120px]">
				<label for="granularity-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.granularity()}
				</label>
				<select
					id="granularity-filter"
					bind:value={selectedGranularity}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					<option value="monthly">{m.monthly()}</option>
					<option value="weekly">{m.weekly()}</option>
				</select>
			</div>

			<!-- Folder Filter -->
			<div class="min-w-[160px]">
				<label for="folder-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.folder()}
				</label>
				<select
					id="folder-filter"
					bind:value={selectedFolder}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					<option value="">{m.allFolders()}</option>
					{#each data.allFolders as folder}
						<option value={folder.id}>{folder.name}</option>
					{/each}
				</select>
			</div>

			<!-- Assigned To Filter -->
			<div class="min-w-[160px]">
				<label for="assigned-to-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.assignedTo()}
				</label>
				<select
					id="assigned-to-filter"
					bind:value={selectedAssignedTo}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					<option value="">{m.allActors()}</option>
					{#each data.allActors as actor}
						<option value={actor.id}>{actor.str || actor.name}</option>
					{/each}
				</select>
			</div>

			<!-- Applied Controls Filter -->
			<div class="min-w-[160px]">
				<label for="applied-controls-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.appliedControls()}
				</label>
				<select
					id="applied-controls-filter"
					bind:value={selectedAppliedControls}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					<option value="">{m.allAppliedControls()}</option>
					{#each data.allAppliedControls as control}
						<option value={control.id}>{control.str || control.name}</option>
					{/each}
				</select>
			</div>

			<!-- Status Filter -->
			<div class="min-w-[130px]">
				<label for="status-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.aggregatedStatus()}
				</label>
				<select
					id="status-filter"
					bind:value={selectedStatus}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					<option value="">{m.allStatuses()}</option>
					<option value="completed">{m.completed()}</option>
					<option value="in_progress">{m.inProgress()}</option>
					<option value="pending">{m.pending()}</option>
					<option value="cancelled">{m.cancelled()}</option>
				</select>
			</div>

			<!-- Action Buttons -->
			<div class="flex gap-2">
				<button
					onclick={applyFilters}
					class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					{m.refresh()}
				</button>
				<button
					onclick={resetFilters}
					class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
				>
					{m.reset()}
				</button>
			</div>
		</div>
	</div>

	<!-- Loading overlay -->
	{#if $navigating}
		<div class="flex items-center justify-center py-16">
			<div class="flex items-center gap-3 text-gray-500">
				<i class="fa-solid fa-spinner fa-spin text-xl"></i>
				<span class="text-sm">{m.loading()}...</span>
			</div>
		</div>
	{:else}
		<!-- Data tables -->
		<div class="space-y-8">
			{#each data.folders as folder}
				<div class="border rounded-lg overflow-hidden">
					<div class="bg-gray-100 px-6 py-3 border-b">
						<h2 class="text-xl font-semibold">{folder.folder_name}</h2>
					</div>

					<div class="overflow-x-auto overflow-y-auto max-h-[70vh]">
						<table class="w-full text-sm">
							<thead class="sticky top-0 z-20">
								<tr class="border-b bg-gray-50">
									<th
										class="px-4 py-3 text-left font-semibold sticky left-0 bg-gray-50 z-30"
										class:min-w-[200px]={!compactMode}
										class:min-w-[100px]={compactMode}
									>
										{m.tasks()}
									</th>
									{#each data.buckets as bucket}
										<th
											class="px-2 py-3 text-center font-semibold w-16"
											title={data.granularity === 'weekly' ? `${bucket.start} — ${bucket.end}` : ''}
										>
											{getBucketLabel(bucket)}
											{#if data.buckets.length > 12 || startFormatted.year !== endFormatted.year}
												<div class="text-xs text-gray-500">
													{bucket.key.split('-')[0]}
												</div>
											{/if}
										</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each folder.tasks as task}
									<tr class="border-b hover:bg-gray-50">
										<td
											class="px-4 sticky left-0 bg-white z-10"
											class:py-3={!compactMode}
											class:py-1={compactMode}
										>
											{#if compactMode}
												<!-- Compact: ref_id badge only, or truncated name -->
												{#if task.ref_id}
													<a
														href="/task-templates/{task.id}"
														class="text-xs bg-slate-200 p-1 rounded hover:bg-slate-300"
														title={task.name}
													>
														{task.ref_id}
													</a>
												{:else}
													<a
														href="/task-templates/{task.id}"
														class="text-xs text-blue-600 hover:underline truncate block max-w-[120px]"
														title={task.name}
													>
														{task.name}
													</a>
												{/if}
											{:else}
												<!-- Detailed view -->
												{#if task.ref_id}
													<span class="text-xs bg-slate-200 p-1 rounded">{task.ref_id}</span>
												{/if}
												<a
													href="/task-templates/{task.id}"
													class="font-medium text-blue-600 hover:text-blue-800 hover:underline"
												>
													{task.name}
												</a>
												{#if task.assigned_to && task.assigned_to.length > 0}
													<div class="text-xs text-gray-500 mt-1">
														{task.assigned_to.map((user: { str: string }) => user.str).join(', ')}
													</div>
												{/if}
												{#if task.applied_controls && task.applied_controls.length > 0}
													<div class="text-xs text-gray-700 mt-2">
														<span class="font-medium">{m.appliedControls()}:</span>
														{task.applied_controls
															.map((control: { str: string }) => control.str)
															.join(', ')}
													</div>
												{/if}
											{/if}
										</td>
										{#each data.buckets as bucket}
											{@const bucketData = task.bucket_status?.[bucket.key]}
											{@const status = bucketData?.status ?? null}
											{@const nodeIds = bucketData?.node_ids ?? []}
											{@const firstNodeId = nodeIds.length > 0 ? nodeIds[0] : null}
											<td
												class="px-2 text-center border-l"
												class:py-3={!compactMode}
												class:py-1={compactMode}
											>
												{#if firstNodeId}
													<a
														href="/task-nodes/{firstNodeId}"
														class="flex items-center justify-center w-full rounded {getStatusColor(
															status
														)}"
														class:h-8={!compactMode}
														class:h-5={compactMode}
														title={nodeIds.length > 1
															? `${nodeIds.length} task nodes`
															: 'View task node'}
													>
														{#if nodeIds.length > 1}
															<span class="text-xs text-gray-600">{nodeIds.length}</span>
														{/if}
													</a>
												{:else}
													<div
														class="w-full rounded {getStatusColor(status)}"
														class:h-8={!compactMode}
														class:h-5={compactMode}
													></div>
												{/if}
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{:else}
				<div class="text-center py-12 text-gray-500">{m.noRecurrentTasksFound()}</div>
			{/each}
		</div>

		<!-- Legend -->
		<div class="flex gap-6 justify-center text-sm">
			<div class="flex items-center gap-2">
				<div class="w-6 h-6 bg-green-200 rounded border"></div>
				<span>{m.completed()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-6 h-6 bg-orange-200 rounded border"></div>
				<span>{m.inProgress()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-6 h-6 bg-red-200 rounded border"></div>
				<span>{m.pending()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-6 h-6 bg-gray-200 rounded border"></div>
				<span>{m.cancelled()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-6 h-6 bg-white rounded border"></div>
				<span>{m.noData()}</span>
			</div>
		</div>
	{/if}
</div>
