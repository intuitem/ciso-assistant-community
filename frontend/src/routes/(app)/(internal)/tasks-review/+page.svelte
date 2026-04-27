<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { goto } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set(m.tasksReview());

	// View settings
	let compactMode = $state(false);
	let filtersExpanded = $state(true);

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

	function toMonthFormat(year: number, month: number): string {
		return `${year}-${String(month).padStart(2, '0')}`;
	}

	function parseMonthFormat(value: string): { year: number; month: number } | null {
		if (!value || !value.includes('-')) return null;
		const [year, month] = value.split('-').map(Number);
		if (
			!year ||
			!month ||
			isNaN(year) ||
			isNaN(month) ||
			month < 1 ||
			month > 12 ||
			year < 1900 ||
			year > 2100
		) {
			return null;
		}
		return { year, month };
	}

	function getBucketLabel(bucket: { key: string; label: string }, granularity: string): string {
		if (granularity === 'monthly') {
			const parts = bucket.key.split('-');
			const monthIndex = parseInt(parts[1]) - 1;
			return getMonthName(monthIndex);
		}
		return bucket.label;
	}

	let startPeriod = $state(toMonthFormat(data.startYear, data.startMonth));
	let endPeriod = $state(toMonthFormat(data.endYear, data.endMonth));
	let selectedFolder = $state(data.selectedFolder);
	let selectedGranularity = $state(data.selectedGranularity || 'monthly');
	let selectedAssignedTo = $state(data.selectedAssignedTo || '');
	let selectedAppliedControls = $state(data.selectedAppliedControls || '');
	let selectedStatus = $state(data.selectedStatus || '');

	let startFormatted = $derived.by(() => {
		const parsed = parseMonthFormat(startPeriod);
		if (!parsed)
			return {
				year: data.startYear,
				month: data.startMonth,
				label: getMonthName(data.startMonth - 1)
			};
		return { year: parsed.year, month: parsed.month, label: getMonthName(parsed.month - 1) };
	});

	let endFormatted = $derived.by(() => {
		const parsed = parseMonthFormat(endPeriod);
		if (!parsed)
			return {
				year: data.endYear,
				month: data.endMonth,
				label: getMonthName(data.endMonth - 1)
			};
		return { year: parsed.year, month: parsed.month, label: getMonthName(parsed.month - 1) };
	});

	let filtersValid = $derived.by(() => {
		const start = parseMonthFormat(startPeriod);
		const end = parseMonthFormat(endPeriod);
		if (!start || !end) return false;
		return start.year < end.year || (start.year === end.year && start.month <= end.month);
	});

	function getStatusColor(status: string | null): string {
		if (!status) return 'bg-white border border-dashed border-gray-200';
		if (status === 'completed') return 'bg-green-100 border border-green-300';
		if (status === 'in_progress') return 'bg-violet-100 border border-violet-300';
		if (status === 'pending') return 'bg-red-100 border border-red-300';
		if (status === 'cancelled') return 'bg-gray-100 border border-gray-300';
		return 'bg-white border border-dashed border-gray-200';
	}

	function applyFilters() {
		const start = parseMonthFormat(startPeriod);
		const end = parseMonthFormat(endPeriod);
		if (!start || !end) return;
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
		goto(`/tasks-review?${params.toString()}`);
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
		goto('/tasks-review');
	}

	let activeFilterCount = $derived(
		[selectedFolder, selectedAssignedTo, selectedAppliedControls, selectedStatus].filter(Boolean)
			.length
	);
</script>

<div class="space-y-5 p-6">
	<!-- Header bar -->
	<div class="flex items-start justify-between gap-4">
		<div
			class="flex items-center gap-2 bg-white/90 border border-gray-200 rounded-lg px-3 py-1.5 shadow-sm"
		>
			<span class="text-sm font-semibold text-gray-800">
				{startFormatted.label}
				{startFormatted.year}
			</span>
			<i class="fa-solid fa-arrow-right text-[10px] text-gray-400"></i>
			<span class="text-sm font-semibold text-gray-800">
				{endFormatted.label}
				{endFormatted.year}
			</span>
			{#if selectedGranularity === 'weekly'}
				<span
					class="inline-flex items-center text-[10px] font-bold uppercase tracking-wider bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded"
					>{m.weekly()}</span
				>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150
					{compactMode
					? 'bg-violet-50 border-violet-300 text-violet-700'
					: 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300'}"
				onclick={() => (compactMode = !compactMode)}
				title={compactMode ? m.detailedView() : m.compactView()}
			>
				<i class="fa-solid {compactMode ? 'fa-expand' : 'fa-compress'} text-[10px]"></i>
				<span>{compactMode ? m.detailedView() : m.compactView()}</span>
			</button>
			<button
				type="button"
				class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all duration-150
					{filtersExpanded
					? 'bg-violet-50 border-violet-300 text-violet-700'
					: 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50 hover:border-gray-300'}"
				onclick={() => (filtersExpanded = !filtersExpanded)}
			>
				<i class="fa-solid fa-sliders text-[10px]"></i>
				<span>{m.filters()}</span>
				{#if activeFilterCount > 0}
					<span
						class="inline-flex items-center justify-center w-4 h-4 text-[9px] font-bold rounded-full bg-violet-600 text-white"
						>{activeFilterCount}</span
					>
				{/if}
			</button>
		</div>
	</div>

	<!-- Collapsible Filters -->
	{#if filtersExpanded}
		<div class="bg-gray-50/80 border border-gray-200 rounded-xl p-4 transition-all duration-200">
			<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 items-end">
				<div>
					<label
						for="start-period-filter"
						class="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1"
						>{m.startPeriod()}</label
					>
					<input
						id="start-period-filter"
						type="month"
						bind:value={startPeriod}
						class="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
					/>
				</div>
				<div>
					<label
						for="end-period-filter"
						class="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1"
						>{m.endPeriod()}</label
					>
					<input
						id="end-period-filter"
						type="month"
						bind:value={endPeriod}
						class="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
					/>
				</div>
				<div>
					<label
						for="granularity-filter"
						class="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1"
						>{m.granularity()}</label
					>
					<select
						id="granularity-filter"
						bind:value={selectedGranularity}
						class="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
					>
						<option value="monthly">{m.monthly()}</option>
						<option value="weekly">{m.weekly()}</option>
					</select>
				</div>

				<!-- Filter dropdowns — streamed -->
				{#await data.filterData}
					<div class="col-span-4 flex items-end">
						<div class="flex items-center gap-2 text-xs text-gray-400 py-2">
							<i class="fa-solid fa-spinner fa-spin"></i>
							{m.loading()}...
						</div>
					</div>
				{:then filters}
					<div>
						<label
							for="folder-filter"
							class="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1"
							>{m.folder()}</label
						>
						<select
							id="folder-filter"
							bind:value={selectedFolder}
							class="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
						>
							<option value="">{m.allFolders()}</option>
							{#each filters.allFolders as folder}
								<option value={folder.id}>{folder.name}</option>
							{/each}
						</select>
					</div>
					<div>
						<label
							for="assigned-to-filter"
							class="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1"
							>{m.assignedTo()}</label
						>
						<select
							id="assigned-to-filter"
							bind:value={selectedAssignedTo}
							class="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
						>
							<option value="">{m.allActors()}</option>
							{#each filters.allActors as actor}
								<option value={actor.id}>{actor.str || actor.name}</option>
							{/each}
						</select>
					</div>
					<div>
						<label
							for="applied-controls-filter"
							class="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1"
							>{m.appliedControls()}</label
						>
						<select
							id="applied-controls-filter"
							bind:value={selectedAppliedControls}
							class="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
						>
							<option value="">{m.allAppliedControls()}</option>
							{#each filters.allAppliedControls as control}
								<option value={control.id}>{control.str || control.name}</option>
							{/each}
						</select>
					</div>
				{/await}

				<div>
					<label
						for="status-filter"
						class="block text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-1"
						>{m.aggregatedStatus()}</label
					>
					<select
						id="status-filter"
						bind:value={selectedStatus}
						class="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent transition-all"
					>
						<option value="">{m.allStatuses()}</option>
						<option value="completed">{m.completed()}</option>
						<option value="in_progress">{m.inProgress()}</option>
						<option value="pending">{m.pending()}</option>
						<option value="cancelled">{m.cancelled()}</option>
					</select>
				</div>

				<div class="flex gap-2">
					<button
						onclick={applyFilters}
						disabled={!filtersValid}
						class="flex-1 px-3 py-1.5 text-sm font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-400 focus:ring-offset-1 transition-all duration-150
							{filtersValid
							? 'bg-violet-600 text-white hover:bg-violet-500'
							: 'bg-gray-300 text-gray-500 cursor-not-allowed'}"
					>
						{m.refresh()}
					</button>
					<button
						onclick={resetFilters}
						class="px-3 py-1.5 text-sm text-gray-500 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-300 transition-all duration-150"
						title={m.reset()}
					>
						<i class="fa-solid fa-rotate-left text-xs"></i>
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Review data — streamed -->
	{#await data.reviewData}
		<div class="space-y-6">
			{#each [1, 2] as _}
				<div class="border border-gray-200 rounded-xl overflow-hidden animate-pulse">
					<div class="bg-gray-100 px-6 py-3 border-b">
						<div class="h-5 w-40 bg-gray-200 rounded"></div>
					</div>
					<div class="p-4 space-y-3">
						{#each [1, 2, 3] as __}
							<div class="flex gap-3 items-center">
								<div class="h-4 w-32 bg-gray-100 rounded"></div>
								<div class="flex-1 flex gap-2">
									{#each [1, 2, 3, 4, 5, 6] as ___}
										<div class="h-6 flex-1 bg-gray-50 rounded"></div>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{:then review}
		{@const folders = review.folders || []}
		{@const buckets = review.buckets || []}
		{@const granularity = review.granularity || 'monthly'}

		<div class="space-y-6">
			{#each folders as folder}
				<div class="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
					<div
						class="px-5 py-3 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white flex items-center gap-3"
					>
						<div class="w-1 h-5 rounded-full bg-violet-500"></div>
						<h2 class="text-base font-semibold text-gray-800">{folder.folder_name}</h2>
						<span class="text-xs text-gray-400"
							>{folder.tasks.length}
							{m.tasks().toLowerCase()}</span
						>
					</div>

					<div class="overflow-x-auto overflow-y-auto max-h-[70vh]">
						<table class="w-full text-sm">
							<thead class="sticky top-0 z-20">
								<tr class="bg-gray-50/95 backdrop-blur-sm border-b border-gray-200">
									<th
										class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-400 sticky left-0 bg-gray-50/95 backdrop-blur-sm z-30"
										class:min-w-[220px]={!compactMode}
										class:min-w-[100px]={compactMode}
									>
										{m.tasks()}
									</th>
									{#each buckets as bucket}
										<th
											class="px-1 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider text-gray-400 w-14"
											title={granularity === 'weekly' ? `${bucket.start} — ${bucket.end}` : ''}
										>
											{getBucketLabel(bucket, granularity)}
											{#if buckets.length > 12 || startFormatted.year !== endFormatted.year}
												<div class="text-[10px] text-gray-300 font-normal normal-case">
													{bucket.key.split('-')[0]}
												</div>
											{/if}
										</th>
									{/each}
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-100">
								{#each folder.tasks as task}
									<tr class="hover:bg-violet-50/30 transition-colors duration-100">
										<td
											class="px-4 sticky left-0 z-10 bg-white"
											class:py-2.5={!compactMode}
											class:py-1.5={compactMode}
										>
											{#if compactMode}
												{#if task.ref_id}
													<Anchor
														href="/task-templates/{task.id}"
														class="inline-block text-[11px] font-mono font-medium bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded hover:bg-violet-100 hover:text-violet-700 transition-colors"
														title={task.name}
													>
														{task.ref_id}
													</Anchor>
												{:else}
													<Anchor
														href="/task-templates/{task.id}"
														class="text-xs text-gray-700 hover:text-violet-600 truncate block max-w-[120px] transition-colors"
														title={task.name}
													>
														{task.name}
													</Anchor>
												{/if}
											{:else}
												<div class="flex flex-col gap-0.5">
													<div class="flex items-center gap-2">
														{#if task.ref_id}
															<span
																class="inline-block text-[10px] font-mono font-medium bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded shrink-0"
																>{task.ref_id}</span
															>
														{/if}
														<Anchor
															href="/task-templates/{task.id}"
															class="font-medium text-sm text-gray-800 hover:text-violet-600 transition-colors"
														>
															{task.name}
														</Anchor>
													</div>
													{#if task.assigned_to && task.assigned_to.length > 0}
														<div class="text-[11px] text-gray-400 flex items-center gap-1">
															<i class="fa-solid fa-user text-[9px]"></i>
															{task.assigned_to.map((user: { str: string }) => user.str).join(', ')}
														</div>
													{/if}
													{#if task.applied_controls && task.applied_controls.length > 0}
														<div class="text-[11px] text-gray-400 flex items-center gap-1">
															<i class="fa-solid fa-shield-halved text-[9px]"></i>
															{task.applied_controls
																.map((control: { str: string }) => control.str)
																.join(', ')}
														</div>
													{/if}
												</div>
											{/if}
										</td>
										{#each buckets as bucket}
											{@const bucketData = task.bucket_status?.[bucket.key]}
											{@const status = bucketData?.status ?? null}
											{@const nodeIds = bucketData?.node_ids ?? []}
											{@const firstNodeId = nodeIds.length > 0 ? nodeIds[0] : null}
											<td
												class="px-1 text-center"
												class:py-2.5={!compactMode}
												class:py-1.5={compactMode}
											>
												{#if firstNodeId}
													<Anchor
														href="/task-nodes/{firstNodeId}"
														label={task.name}
														class="flex items-center justify-center w-full rounded-md {getStatusColor(
															status
														)} hover:opacity-80 transition-opacity {compactMode ? 'h-4' : 'h-7'}"
														title={nodeIds.length > 1
															? `${nodeIds.length} ${m.taskNodes().toLowerCase()}`
															: m.viewTaskNode()}
													>
														{#if nodeIds.length > 1 && !compactMode}
															<span class="text-[10px] font-medium text-gray-500"
																>{nodeIds.length}</span
															>
														{/if}
													</Anchor>
												{:else}
													<div
														class="w-full rounded-md {getStatusColor(status)}"
														class:h-7={!compactMode}
														class:h-4={compactMode}
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
				<div
					class="text-center py-16 text-gray-400 border border-dashed border-gray-200 rounded-xl"
				>
					<i class="fa-solid fa-calendar-xmark text-3xl mb-3 text-gray-300"></i>
					<p>{m.noRecurrentTasksFound()}</p>
				</div>
			{/each}
		</div>

		<!-- Legend -->
		<div
			class="flex items-center gap-5 justify-center text-xs text-gray-500 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-xl px-5 py-2.5"
		>
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-3 rounded-sm bg-green-100 border border-green-300"></div>
				<span>{m.completed()}</span>
			</div>
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-3 rounded-sm bg-violet-100 border border-violet-300"></div>
				<span>{m.inProgress()}</span>
			</div>
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-3 rounded-sm bg-red-100 border border-red-300"></div>
				<span>{m.pending()}</span>
			</div>
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-3 rounded-sm bg-gray-100 border border-gray-300"></div>
				<span>{m.cancelled()}</span>
			</div>
			<div class="flex items-center gap-1.5">
				<div class="w-3 h-3 rounded-sm bg-white border border-dashed border-gray-200"></div>
				<span>{m.noData()}</span>
			</div>
		</div>
	{/await}
</div>
