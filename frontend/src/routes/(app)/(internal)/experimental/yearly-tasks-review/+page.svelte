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

	const months = [
		'Jan',
		'Feb',
		'Mar',
		'Apr',
		'May',
		'Jun',
		'Jul',
		'Aug',
		'Sep',
		'Oct',
		'Nov',
		'Dec'
	];

	// Generate year options (current year ± 5 years)
	const currentYear = new Date().getFullYear();
	const yearOptions = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i);

	let selectedYear = $state(data.selectedYear);
	let selectedFolder = $state(data.selectedFolder);

	function getStatusColor(status: string | null): string {
		if (!status) return 'bg-white';
		if (status === 'completed') return 'bg-green-200';
		if (status === 'in_progress') return 'bg-orange-200';
		if (status === 'pending') return 'bg-red-200';
		return 'bg-white';
	}

	function applyFilters() {
		const params = new URLSearchParams();
		if (selectedYear) params.set('year', selectedYear);
		if (selectedFolder) params.set('folder', selectedFolder);
		goto(`/experimental/yearly-tasks-review?${params.toString()}`);
	}

	function resetFilters() {
		selectedYear = currentYear.toString();
		selectedFolder = '';
		goto('/experimental/yearly-tasks-review');
	}
</script>

<div class="bg-white p-8 space-y-8">
	<div>
		<h1 class="text-3xl font-bold mb-2">{m.yearlyTasksReview()} - {selectedYear}</h1>
		<p class="text-gray-600">{m.reviewRecurrentTasksStatusByMonth()}</p>
	</div>

	<!-- Filters -->
	<div class="bg-gray-50 p-4 rounded-lg border">
		<div class="flex gap-4 items-end flex-wrap">
			<div class="flex-1 min-w-[200px]">
				<label for="year-filter" class="block text-sm font-medium text-gray-700 mb-1">
					{m.year()}
				</label>
				<select
					id="year-filter"
					bind:value={selectedYear}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					{#each yearOptions as year}
						<option value={year.toString()}>{year}</option>
					{/each}
				</select>
			</div>

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

			<div class="flex gap-2">
				<button
					onclick={applyFilters}
					class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
				>
					{m.apply()}
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
								{#each months as month}
									<th class="px-2 py-3 text-center font-semibold w-16">{month}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each folder.tasks as task}
								<tr class="border-b hover:bg-gray-50">
									<td class="px-4 py-3 sticky left-0 bg-white z-10">
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
									{#each months as _, idx}
										{@const monthNum = String(idx + 1)}
										{@const status = task.monthly_status?.[monthNum]}
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
