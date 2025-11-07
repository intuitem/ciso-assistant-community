<script lang="ts">
	import { m } from '$paraglide/messages';

	interface TimelineEntry {
		folder: string;
		asset: string;
		data: Record<
			number,
			{
				value: number;
				hexcolor?: string;
				name?: string;
				description?: string;
			}
		>;
	}

	interface Props {
		data: TimelineEntry[];
	}

	let { data }: Props = $props();

	// Extract the x-axis values
	const xAxisPoints =
		Array.isArray(data) && data.length > 0
			? Object.keys(data[0].data)
					.map(Number)
					.sort((a, b) => a - b)
			: [];

	// Extract unique impact levels for legend from the data
	const impactLevels = $derived.by(() => {
		const levelsMap = new Map<
			number,
			{ value: number; name: string; description: string; hexcolor: string }
		>();

		if (Array.isArray(data) && data.length > 0) {
			data.forEach((entry) => {
				Object.values(entry.data).forEach((point) => {
					if (
						point.name &&
						point.hexcolor &&
						point.value >= 0 &&
						point.name !== '--' &&
						!levelsMap.has(point.value)
					) {
						levelsMap.set(point.value, {
							value: point.value,
							name: point.name,
							description: point.description || '',
							hexcolor: point.hexcolor
						});
					}
				});
			});
		}

		return Array.from(levelsMap.values()).sort((a, b) => a.value - b.value);
	});

	function formatTimePoint(seconds: number) {
		if (seconds === 0) return '0';

		const days = Math.floor(seconds / 86400);
		const hours = Math.floor((seconds % 86400) / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);

		const parts = [];
		if (days) parts.push(`${m['dayCount']({ count: days })}`);
		if (hours) parts.push(`${m['hourCount']({ count: hours })}`);
		if (minutes) parts.push(`${m['minuteCount']({ count: minutes })}`);

		return parts.join(' ');
	}

	// Helper to determine if a cell represents an impact change
	function isImpactChange(entry: TimelineEntry, currentIndex: number) {
		if (currentIndex === 0) return true;

		const currentPoint = xAxisPoints[currentIndex];
		const previousPoint = xAxisPoints[currentIndex - 1];

		return entry.data[currentPoint].value !== entry.data[previousPoint].value;
	}
</script>

<div class="space-y-4">
	<!-- Legend -->
	{#if impactLevels.length > 0}
		<div class="bg-white shadow-sm rounded-lg p-4">
			<div class="flex flex-wrap gap-4">
				{#each impactLevels as level}
					<div class="flex items-center gap-2">
						<div
							class="w-6 h-6 rounded border border-gray-300 flex-shrink-0"
							style="background-color: {level.hexcolor}"
						></div>
						<div class="flex flex-col">
							<span class="text-sm font-semibold text-gray-800">{level.name}</span>
							{#if level.description}
								<span class="text-xs text-gray-600">{level.description}</span>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Timeline Table -->
	{#if Array.isArray(data) && data.length > 0}
		<div class="bg-white shadow-sm overflow-x-auto">
			<div class="w-full">
				<table class="min-w-full border-collapse">
					<thead>
						<tr class="bg-gray-100">
							<th class="sticky-col px-4 py-2 text-left font-medium text-gray-600 bg-gray-100">
								{m.asset()}
							</th>
							{#each xAxisPoints as point, i}
								<th class="px-4 py-2 text-center font-medium text-gray-600">
									T{i}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each data as entry}
							<tr class="border-t border-gray-200">
								<td class="sticky-col px-4 py-2 font-medium bg-white">
									{entry.folder}/{entry.asset}
								</td>
								{#each xAxisPoints as point, i}
									<td
										class="px-4 py-2 text-center"
										style="background-color: {entry.data[point].hexcolor || '#f9fafb'};
										       {!isImpactChange(entry, i) ? 'border-left: none;' : ''}"
									>
										{#if isImpactChange(entry, i)}
											<div class="font-medium">{entry.data[point].name || '--'}</div>
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
					<tfoot>
						<tr class="bg-gray-50 border-t-2 border-gray-200">
							<td class="sticky-col px-4 py-2 font-medium text-gray-600 capitalize bg-gray-50">
								{m.time()}
							</td>
							{#each xAxisPoints as point}
								<td class="px-4 py-2 text-center text-sm text-gray-600">
									{formatTimePoint(point)}
								</td>
							{/each}
						</tr>
					</tfoot>
				</table>
			</div>
		</div>
	{:else}
		<div class="bg-white shadow-sm rounded-lg p-8 text-center text-gray-500">
			{m.noDataAvailable()}
		</div>
	{/if}
</div>

<style>
	table {
		border-collapse: separate;
		border-spacing: 0;
		width: 100%;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		border-radius: 6px;
	}

	th,
	td {
		border-right: 1px solid rgba(0, 0, 0, 0.05);
	}

	th:last-child,
	td:last-child {
		border-right: none;
	}

	/* Sticky first column */
	.sticky-col {
		position: sticky;
		left: 0;
		z-index: 10;
		box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
		min-width: 200px;
		max-width: 300px;
	}

	thead .sticky-col {
		z-index: 20;
	}

	/* Add visual cues for impact transitions */
	td[style*='border-left: none'] {
		position: relative;
	}

	td[style*='border-left: none']::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 1px;
		background: rgba(0, 0, 0, 0.05);
		opacity: 0.3;
	}

	/* Footer styling */
	tfoot td {
		font-size: 0.85rem;
		padding-top: 0.75rem;
		padding-bottom: 0.75rem;
	}
</style>
