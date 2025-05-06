<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import { pageTitle } from '$lib/utils/stores';
	pageTitle.set('Visual Analysis');

	// Extract the x-axis values from the first entry's data
	// Assuming data structure from build_table method
	const xAxisPoints =
		data.data.length > 0
			? Object.keys(data.data[0].data)
					.map(Number)
					.sort((a, b) => a - b)
			: [];

	// Helper function to convert seconds to human-readable format
	function formatTimePoint(seconds: number) {
		if (seconds === 0) return '0';

		const days = Math.floor(seconds / 86400);
		const hours = Math.floor((seconds % 86400) / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);

		const parts = [];
		if (days) parts.push(`${days}d`);
		if (hours) parts.push(`${hours}h`);
		if (minutes) parts.push(`${minutes}m`);

		return parts.join(' ');
	}
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full">
		<table class="min-w-full border-collapse">
			<thead>
				<tr class="bg-gray-100">
					<th class="px-4 py-2 text-left font-medium text-gray-600">Asset</th>
					{#each xAxisPoints as point}
						<th class="px-4 py-2 text-center font-medium text-gray-600">
							{formatTimePoint(point)}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each data.data as entry}
					<tr class="border-t border-gray-200">
						<td class="px-4 py-2 font-medium">{entry.asset}</td>
						{#each xAxisPoints as point}
							{#if entry.data[point]}
								<td
									class="px-4 py-2 text-center"
									style="background-color: {entry.data[point].hexcolor || '#f9fafb'}"
								>
									<div class="font-medium">{entry.data[point].name || '--'}</div>
									<div class="text-xs text-gray-500">
										{entry.data[point].value >= 0 ? entry.data[point].value : '--'}
									</div>
								</td>
							{:else}
								<td class="px-4 py-2 text-center bg-gray-50">--</td>
							{/if}
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
