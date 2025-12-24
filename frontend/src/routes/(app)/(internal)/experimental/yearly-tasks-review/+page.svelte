<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { goto } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set(m.yearlyTasksReview());

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

	let startPeriod = $state(toMonthFormat(data.startYear, data.startMonth));
	let endPeriod = $state(toMonthFormat(data.endYear, data.endMonth));
	let selectedFolder = $state(data.selectedFolder);

	// Generate the list of months to display based on date range
	function getMonthsInRange() {
		const result: Array<{ year: number; month: number; label: string }> = [];
		const start = parseMonthFormat(startPeriod);
		const end = parseMonthFormat(endPeriod);
		let current = new Date(start.year, start.month - 1, 1);
		const endDate = new Date(end.year, end.month - 1, 1);

		while (current <= endDate) {
			const year = current.getFullYear();
			const month = current.getMonth() + 1;
			const label = getMonthName(month - 1);
			result.push({ year, month, label });

			// Move to next month
			current.setMonth(current.getMonth() + 1);
		}

		return result;
	}

	let monthsToDisplay = $derived(getMonthsInRange());

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
		if (selectedFolder) params.set('folder', selectedFolder);
		goto(`/experimental/yearly-tasks-review?${params.toString()}`);
	}

	function resetFilters() {
		const currentYear = new Date().getFullYear();
		startPeriod = toMonthFormat(currentYear, 1);
		endPeriod = toMonthFormat(currentYear, 12);
		selectedFolder = '';
		goto('/experimental/yearly-tasks-review');
	}
</script>

<div class="bg-white p-8 space-y-8">
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
		</p>
	</div>

	<!-- Filters -->
	<div class="bg-gray-50 p-4 rounded-lg border">
		<div class="flex gap-4 items-end flex-wrap">
			<!-- Start Period -->
			<div class="min-w-[160px]">
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
			<div class="min-w-[160px]">
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

			<!-- Folder Filter -->
			<div class="flex-1 min-w-[200px]">
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

	<div class="space-y-8">
		{#each data.folders as folder}
			<div class="border rounded-lg overflow-hidden">
				<div class="bg-gray-100 px-6 py-3 border-b">
					<h2 class="text-xl font-semibold">{folder.folder_name}</h2>
				</div>

				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="border-b bg-gray-50">
								<th
									class="px-4 py-3 text-left font-semibold min-w-[200px] sticky left-0 bg-gray-50 z-10"
								>
									{m.tasks()}
								</th>
								<th class="px-2 py-3 text-center font-semibold w-16">{m.frequency()}</th>
								{#each monthsToDisplay as monthInfo}
									<th class="px-2 py-3 text-center font-semibold w-16">
										{monthInfo.label}
										{#if monthsToDisplay.length > 12 || startFormatted.year !== endFormatted.year}
											<div class="text-xs text-gray-500">{monthInfo.year}</div>
										{/if}
									</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each folder.tasks as task}
								<tr class="border-b hover:bg-gray-50">
									<td class="px-4 py-3 sticky left-0 bg-white z-10">
										{#if task.ref_id}
											<div class="">
												<span class="text-xs bg-slate-200 p-1 rounded">{task.ref_id}</span>
											</div>
										{/if}
										<a
											href="/task-templates/{task.id}"
											class="font-medium text-blue-600 hover:text-blue-800 hover:underline"
										>
											{task.name}
										</a>
										{#if task.assigned_to && task.assigned_to.length > 0}
											<div class="text-xs text-gray-500 mt-1">
												{task.assigned_to.map((user) => user.str).join(', ')}
											</div>
										{/if}
										{#if task.applied_controls && task.applied_controls.length > 0}
											<div class="text-xs text-gray-700 mt-2">
												<span class="font-medium">{m.appliedControls()}:</span>
												{task.applied_controls.map((control) => control.str).join(', ')}
											</div>
										{/if}
									</td>
									<td class="px-2 py-3 text-center text-xs">
										{#if task.schedule && task.schedule.frequency}
											<span class="inline-block px-2 py-1 bg-blue-100 text-blue-800 rounded">
												{task.schedule.frequency.charAt(0)}
											</span>
										{/if}
									</td>
									{#each monthsToDisplay as monthInfo}
										{@const key = `${monthInfo.year}-${String(monthInfo.month).padStart(2, '0')}`}
										{@const status = task.monthly_status?.[key]}
										<td class="px-2 py-3 text-center border-l">
											<div class="w-full h-8 rounded {getStatusColor(status)}"></div>
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
			<div class="w-6 h-6 bg-white rounded border"></div>
			<span>{m.noData()}</span>
		</div>
	</div>
</div>
