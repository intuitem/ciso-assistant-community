<script lang="ts">
	import { m } from '$paraglide/messages';
	import { isDark } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';

	interface TimelineEntry {
		folder: string;
		asset: string;
		qualification?: string | null;
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

	let groupBy = $state<'asset' | 'qualification'>('asset');

	const hasQualifications = $derived(Array.isArray(data) && data.some((e) => e.qualification));

	const assetLabel = (e: TimelineEntry) => `${e.folder}/${e.asset}`;
	const qualificationLabel = (e: TimelineEntry) =>
		e.qualification ? safeTranslate(e.qualification) : '--';

	const groups = $derived.by(() => {
		const key = groupBy === 'asset' ? assetLabel : qualificationLabel;
		const map = new Map<string, TimelineEntry[]>();
		for (const e of Array.isArray(data) ? data : []) {
			map.set(key(e), [...(map.get(key(e)) ?? []), e]);
		}
		return [...map.entries()];
	});

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

	// A "--" / no-impact cell carries a white hexcolor from the backend, which stays glaringly
	// light in dark mode. Treat those as empty and let them use the theme surface instead.
	function isEmptyCell(point: { name?: string }) {
		return !point?.name || point.name === '--';
	}

	// Empty cells follow the theme surface (bg + adaptive text); impact cells keep their fixed
	// color with black/white text picked by luminance.
	function cellBg(point: { hexcolor?: string; name?: string }) {
		if (isEmptyCell(point)) return 'var(--color-surface-100-900)';
		return point.hexcolor || 'var(--color-surface-100-900)';
	}
	function cellTextClass(point: { hexcolor?: string; name?: string }) {
		if (isEmptyCell(point)) return 'text-surface-950-50';
		return point.hexcolor && isDark(point.hexcolor) ? 'text-white' : 'text-surface-950';
	}

	// Helper to determine if a cell represents an impact change
	function isImpactChange(entry: TimelineEntry, currentIndex: number) {
		if (currentIndex === 0) return true;

		const currentPoint = xAxisPoints[currentIndex];
		const previousPoint = xAxisPoints[currentIndex - 1];

		return entry.data[currentPoint].value !== entry.data[previousPoint].value;
	}
</script>

{#snippet assetCell(e: TimelineEntry)}
	<div class="flex flex-col items-start gap-1">
		<span>{e.asset}</span>
		<span class="badge preset-tonal-secondary text-xs">{e.folder}</span>
	</div>
{/snippet}

<div class="space-y-4">
	{#if hasQualifications}
		<div class="flex gap-2 no-print">
			<button
				class="btn btn-sm {groupBy === 'asset' ? 'preset-filled-primary-500' : 'preset-tonal'}"
				onclick={() => (groupBy = 'asset')}>{m.asset()}</button
			>
			<button
				class="btn btn-sm {groupBy === 'qualification'
					? 'preset-filled-primary-500'
					: 'preset-tonal'}"
				onclick={() => (groupBy = 'qualification')}>{m.qualification()}</button
			>
		</div>
	{/if}

	<!-- Legend -->
	{#if impactLevels.length > 0}
		<div class="bg-surface-50-950 shadow-sm rounded-lg p-4">
			<div class="flex flex-wrap gap-4">
				{#each impactLevels as level}
					<div class="flex items-center gap-2">
						<div
							class="w-6 h-6 rounded border border-surface-300-700 flex-shrink-0"
							style="background-color: {level.hexcolor}"
						></div>
						<div class="flex flex-col">
							<span class="text-sm font-semibold text-surface-950-50">{level.name}</span>
							{#if level.description}
								<span class="text-xs text-surface-600-400">{level.description}</span>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Timeline Table -->
	{#if Array.isArray(data) && data.length > 0}
		<div class="bg-surface-50-950 shadow-sm overflow-x-auto">
			<div class="w-full">
				<table class="min-w-full border-collapse">
					<thead>
						<tr class="bg-surface-100-900">
							<th
								class="sticky-col px-4 py-2 text-left font-medium text-surface-600-400 bg-surface-100-900"
							>
								{groupBy === 'asset' ? m.asset() : m.qualification()}
							</th>
							{#if hasQualifications}
								<th class="px-4 py-2 text-left font-medium text-surface-600-400">
									{groupBy === 'asset' ? m.qualification() : m.asset()}
								</th>
							{/if}
							{#each xAxisPoints as point, i}
								<th class="px-4 py-2 text-center font-medium text-surface-600-400">
									T{i}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each groups as [label, entries], g}
							{#each entries as entry, j}
								<tr class:group-start={j === 0}>
									{#if j === 0}
										<td
											class="sticky-col px-4 py-2 font-medium {g % 2
												? 'bg-surface-100-900'
												: 'bg-surface-50-950'}"
											rowspan={entries.length}
										>
											{#if groupBy === 'asset'}
												{@render assetCell(entry)}
											{:else}
												{label}
											{/if}
										</td>
									{/if}
									{#if hasQualifications}
										<td
											class="px-4 py-2 text-sm {g % 2 ? 'bg-surface-100-900' : 'bg-surface-50-950'}"
										>
											{#if groupBy === 'asset'}
												{qualificationLabel(entry)}
											{:else}
												{@render assetCell(entry)}
											{/if}
										</td>
									{/if}
									{#each xAxisPoints as point, i}
										<td
											class="px-4 py-2 text-center"
											style="background-color: {cellBg(entry.data[point])};
										       {i < xAxisPoints.length - 1 && !isImpactChange(entry, i + 1) ? 'border-right: none;' : ''}"
										>
											{#if isImpactChange(entry, i)}
												<div class="font-medium {cellTextClass(entry.data[point])}">
													{entry.data[point].name || '--'}
												</div>
											{/if}
										</td>
									{/each}
								</tr>
							{/each}
						{/each}
					</tbody>
					<tfoot>
						<tr class="bg-surface-50-950 border-t-2 border-surface-200-800">
							<td
								class="sticky-col px-4 py-2 font-medium text-surface-600-400 capitalize bg-surface-50-950"
								colspan={hasQualifications ? 2 : 1}
							>
								{m.time()}
							</td>
							{#each xAxisPoints as point}
								<td class="px-4 py-2 text-center text-sm text-surface-600-400">
									{formatTimePoint(point)}
								</td>
							{/each}
						</tr>
					</tfoot>
				</table>
			</div>
		</div>
	{:else}
		<div class="bg-surface-50-950 shadow-sm rounded-lg p-8 text-center text-surface-600-400">
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
		border-right: 1px solid var(--color-surface-200-800);
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

	/* Footer styling */
	tbody td {
		border-top: 1px solid var(--color-surface-200-800);
	}

	tbody tr.group-start td {
		border-top: 2px solid var(--color-surface-400-600);
	}

	tfoot td {
		font-size: 0.85rem;
		padding-top: 0.75rem;
		padding-bottom: 0.75rem;
	}
</style>
