<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import SimpleCard from './SimpleCard.svelte';

	interface Bucket {
		key: string;
		count: number;
	}

	interface AnalyticsData {
		count: number;
		by_status: Bucket[];
		due_buckets: Bucket[];
		by_assignee: { key: string; label: string; count: number }[];
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
	}

	let { analyticsData = null }: Props = $props();

	const data = $derived(analyticsData);
	const hasAnyData = $derived(!!data && data.count > 0);

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
			const translated = safeTranslate(b.key);
			return {
				name: translated && translated !== b.key ? translated : b.key,
				value: b.count
			};
		});
	}

	const statusValues = $derived(toDonutValues(data?.by_status));
	const commitmentValues = $derived(toDonutValues(data?.commitment?.by_state));

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

	const assigneeBars = $derived({
		labels: (data?.by_assignee ?? []).map((b) => b.label),
		values: (data?.by_assignee ?? []).map((b) => b.count)
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
			<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
				<p class="font-semibold mb-2">{m.status()}</p>
				<DonutChart name="taskAnalyticsStatus" values={statusValues} />
			</div>
			<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
				<p class="font-semibold mb-2">{m.eta()}</p>
				<BarChart
					name="taskAnalyticsDue"
					labels={dueBars.labels}
					values={dueBars.values}
					horizontal={true}
				/>
			</div>
			{#if data.commitment}
				<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
					<p class="font-semibold mb-2">{m.commitment()}</p>
					<DonutChart name="taskAnalyticsCommitment" values={commitmentValues} />
				</div>
			{/if}
			{#if assigneeBars.labels.length}
				<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg">
					<p class="font-semibold mb-2">{m.assignedTo()}</p>
					<BarChart
						name="taskAnalyticsAssignees"
						labels={assigneeBars.labels}
						values={assigneeBars.values}
						horizontal={true}
					/>
				</div>
			{/if}
		</div>
	</div>
{/if}
