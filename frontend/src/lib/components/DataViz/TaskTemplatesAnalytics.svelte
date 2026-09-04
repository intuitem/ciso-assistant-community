<script lang="ts">
	import { goto } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import {
		TASK_STATUS_COLORS as statusColorMap,
		TASK_STATUS_FALLBACK_COLOR as FALLBACK_COLOR
	} from '$lib/utils/taskStatus';
	import { safeTranslate } from '$lib/utils/i18n';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import GroupedBarChart from '$lib/components/Chart/GroupedBarChart.svelte';
	import SimpleCard from './SimpleCard.svelte';

	interface Bucket {
		key: string;
		count: number;
	}

	interface AnalyticsData {
		count: number;
		by_status: Bucket[];
		due_buckets: Bucket[];
		by_assignee: { key: string; label: string; count: number; status_breakdown: Bucket[] }[];
		by_folder: { key: string; label: string; count: number; status_breakdown: Bucket[] }[];
		unassigned: number;
		recurrence: { one_time: number; recurrent: number };
		commitment?: {
			by_state: Bucket[];
			slipped: number;
			breached: number;
		};
	}

	interface Props {
		analyticsData?: AnalyticsData | null;
		// The table filters this page was opened with, so a drill-down keeps them.
		filterSearch?: string;
	}

	let { analyticsData = null, filterSearch = '' }: Props = $props();

	const data = $derived(analyticsData);
	const hasAnyData = $derived(!!data && data.count > 0);

	// Keyed rather than positional: the backend sorts buckets by count, so a
	// positional palette would repaint a status every time the counts shift.
	const commitmentColorMap: Record<string, string> = {
		'--': '#cbd5e1',
		in_negotiation: '#f59e0b',
		committed: '#3b82f6',
		declined: '#ef4444',
		fulfilled: '#22c55e'
	};

	// Same bucket vocabulary as the applied-control analytics, so the two pages read alike.
	const dueLabelMap: Record<string, () => string> = {
		overdue: m.overdue,
		due_30d: m.dueIn30Days,
		due_90d: m.dueIn90Days,
		later: m.laterDue,
		no_eta: m.noEtaSet
	};

	function toDonutValues(buckets: Bucket[] | undefined) {
		return (buckets ?? []).map((b) => {
			// The backend has no status for a template with no occurrence yet.
			if (b.key === '_unset') return { name: m.noStatus(), value: b.count };
			const translated = safeTranslate(b.key);
			return {
				name: translated && translated !== b.key ? translated : b.key,
				value: b.count
			};
		});
	}

	function toColors(buckets: Bucket[] | undefined, palette: Record<string, string>) {
		return (buckets ?? []).map((b) => palette[b.key] ?? FALLBACK_COLOR);
	}

	function statusLabel(key: string) {
		if (key === '_unset') return m.noStatus();
		const translated = safeTranslate(key);
		return translated && translated !== key ? translated : key;
	}

	// Segments carry no status filter of their own: the analytics status and the
	// list's next_occurrence_status disagree for a one-time task whose only
	// occurrence is past, and '_unset' has no filter value at all. Every segment
	// therefore lands on the same place as the assignee name.
	function drillDownHref(assigneeId: string) {
		return listHref('assigned_to', assigneeId);
	}

	function listHref(field: string, value: string) {
		const params = new URLSearchParams(filterSearch);
		// Replace rather than append: both are multi-value filters, so appending
		// would widen the result instead of narrowing it to what was clicked.
		params.delete(field);
		params.append(field, value);
		return `/task-templates?${params.toString()}`;
	}

	const statusValues = $derived(toDonutValues(data?.by_status));
	const statusColors = $derived(toColors(data?.by_status, statusColorMap));
	const commitmentValues = $derived(toDonutValues(data?.commitment?.by_state));
	const commitmentColors = $derived(toColors(data?.commitment?.by_state, commitmentColorMap));

	const dueBars = $derived.by(() => {
		const ordered = ['overdue', 'due_30d', 'due_90d', 'later', 'no_eta'];
		const map = new Map((data?.due_buckets ?? []).map((b) => [b.key, b]));
		const labels: string[] = [];
		const values: number[] = [];
		for (const key of ordered) {
			const bucket = map.get(key);
			if (!bucket) continue;
			labels.push(dueLabelMap[key]?.() ?? key);
			values.push(bucket.count);
		}
		return { labels, values };
	});

	// The backend sorts by count desc; a horizontal ECharts bar puts index 0 at the
	// bottom, so reverse it to read largest-first from the top. Series are driven
	// by the global by_status order so every domain stacks its statuses in the
	// same sequence and shares the donut's colors.
	const folderStack = $derived.by(() => {
		const rows = [...(data?.by_folder ?? [])].reverse();
		const statuses = data?.by_status ?? [];
		return {
			categories: rows.map((row) => row.label),
			// Folder ids in the same order as the categories, so a click on bar i
			// resolves to the domain it was drawn from rather than to its label.
			keys: rows.map((row) => row.key),
			colors: statuses.map((s) => statusColorMap[s.key] ?? FALLBACK_COLOR),
			series: statuses.map((s) => ({
				name: statusLabel(s.key),
				data: rows.map((row) => row.status_breakdown.find((seg) => seg.key === s.key)?.count ?? 0)
			}))
		};
	});

	const overdueCount = $derived(
		(data?.due_buckets ?? []).find((b) => b.key === 'overdue')?.count ?? 0
	);
</script>

{#if !hasAnyData}
	<div class="bg-surface-50-950 p-6 shadow-sm rounded-lg text-center text-surface-600-400">
		{m.noDataAvailable()}
	</div>
{:else if data}
	<div class="space-y-4">
		<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
			<SimpleCard count={String(data.count)} emphasis={true} label={m.taskTemplates()} />
			<SimpleCard count={String(overdueCount)} label={m.overdue()} />
			<SimpleCard count={String(data.unassigned)} label={m.unassigned()} />
			<SimpleCard count={String(data.recurrence.recurrent)} label={m.recurrent()} />
		</div>

		{#if data.commitment}
			<div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
				<SimpleCard count={String(data.commitment.slipped)} label={m.commitmentSlipped()} />
				<SimpleCard count={String(data.commitment.breached)} label={m.commitmentBreached()} />
			</div>
		{/if}

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			{#if statusValues.length > 0}
				<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
					<p class="font-semibold mb-2">{m.status()}</p>
					<div class="h-72">
						<DonutChart
							name="taskAnalyticsStatus"
							values={statusValues}
							colors={statusColors}
							showPercentage={true}
						/>
					</div>
				</div>
			{/if}
			{#if dueBars.labels.length > 0}
				<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
					<p class="font-semibold mb-2">{m.eta()}</p>
					<div class="h-72">
						<BarChart
							name="taskAnalyticsDue"
							labels={dueBars.labels}
							values={dueBars.values}
							horizontal={true}
						/>
					</div>
				</div>
			{/if}
			{#if folderStack.categories.length > 0}
				<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
					<p class="font-semibold mb-2">{m.domains()}</p>
					<div class="h-72">
						<GroupedBarChart
							name="taskAnalyticsFolders"
							categories={folderStack.categories}
							series={folderStack.series}
							colors={folderStack.colors}
							horizontal={true}
							stack="status"
							onSelect={(index) => goto(listHref('folder', folderStack.keys[index]))}
						/>
					</div>
				</div>
			{/if}
			{#if commitmentValues.length > 0}
				<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
					<p class="font-semibold mb-2">{m.commitment()}</p>
					<div class="h-72">
						<DonutChart
							name="taskAnalyticsCommitment"
							values={commitmentValues}
							colors={commitmentColors}
							showPercentage={true}
						/>
					</div>
				</div>
			{/if}
		</div>

		{#if data.by_assignee.length > 0}
			<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
				<p class="font-semibold mb-2">{m.assignedTo()}</p>
				<div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-surface-600-400 mb-3">
					{#each data.by_status as segment (segment.key)}
						<div class="flex items-center gap-1.5">
							<span
								class="inline-block h-2.5 w-2.5 rounded-sm"
								style="background-color: {statusColorMap[segment.key] ?? FALLBACK_COLOR};"
							></span>
							<span>{statusLabel(segment.key)}</span>
						</div>
					{/each}
				</div>
				<table class="w-full text-sm">
					<thead>
						<tr class="text-left text-xs text-surface-600-400 border-b">
							<th class="py-1">{m.assignedTo()}</th>
							<th class="py-1">{m.status()}</th>
							<th class="py-1 text-right">{m.count()}</th>
						</tr>
					</thead>
					<tbody>
						{#each data.by_assignee as row (row.key)}
							<tr class="border-b last:border-b-0">
								<td class="py-1.5">
									<a href={drillDownHref(row.key)} class="hover:underline">{row.label}</a>
								</td>
								<td class="py-1.5 w-1/2">
									<div class="flex h-2 w-full rounded bg-surface-100-900 overflow-hidden">
										{#each row.status_breakdown as segment (segment.key)}
											{@const label = statusLabel(segment.key)}
											<a
												href={drillDownHref(row.key)}
												title="{label}: {segment.count}"
												class="relative h-full group"
												style="width: {(segment.count / row.count) *
													100}%; background-color: {statusColorMap[segment.key] ?? FALLBACK_COLOR};"
											>
												<div
													class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 text-xs whitespace-nowrap bg-gray-900 text-white rounded opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-10 shadow"
												>
													{label}: {segment.count}
												</div>
											</a>
										{/each}
									</div>
								</td>
								<td class="py-1.5 text-right tabular-nums">{row.count}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
{/if}
