<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('Yearly Periodic Tasks Review');

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
	const currentYear = new Date().getFullYear();

	function getStatusColor(status: string | null): string {
		if (!status) return 'bg-white';
		if (status === 'completed') return 'bg-green-200';
		if (status === 'in_progress') return 'bg-orange-200';
		if (status === 'pending') return 'bg-red-200';
		return 'bg-white';
	}
</script>

<div class="bg-white p-8 space-y-8">
	<div>
		<h1 class="text-3xl font-bold mb-2">Yearly Tasks Review - {currentYear}</h1>
		<p class="text-gray-600">Review recurrent tasks status by month</p>
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
									>Task</th
								>
								<th class="px-2 py-3 text-center font-semibold w-16">Freq</th>
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
			<div class="text-center py-12 text-gray-500">No recurrent tasks found</div>
		{/each}
	</div>

	<div class="flex gap-6 justify-center text-sm">
		<div class="flex items-center gap-2">
			<div class="w-6 h-6 bg-green-200 rounded border"></div>
			<span>Completed</span>
		</div>
		<div class="flex items-center gap-2">
			<div class="w-6 h-6 bg-orange-200 rounded border"></div>
			<span>In Progress</span>
		</div>
		<div class="flex items-center gap-2">
			<div class="w-6 h-6 bg-red-200 rounded border"></div>
			<span>Pending</span>
		</div>
		<div class="flex items-center gap-2">
			<div class="w-6 h-6 bg-white rounded border"></div>
			<span>No Data</span>
		</div>
	</div>
</div>
