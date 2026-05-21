<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import SimpleCard from './SimpleCard.svelte';

	interface Bucket {
		key?: string;
		count: number;
		total: number;
		total_display: string;
	}

	interface AnalyticsData {
		count: number;
		count_with_cost: number;
		total_annual_cost: number;
		total_annual_cost_display: string;
		currency: string;
		by_status: (Bucket & { status: string })[];
		by_priority: (Bucket & { priority: string })[];
		by_category: (Bucket & { category: string })[];
		by_csf_function: (Bucket & { csf_function: string })[];
		eta_buckets: { key: string; count: number; total: number; total_display: string }[];
		top_owners: { label: string; count: number; total: number; total_display: string }[];
		top_folders: { label: string; count: number; total: number; total_display: string }[];
	}

	interface Props {
		// Provide either pre-loaded analytics data (server-loaded) ...
		analyticsData?: AnalyticsData | null;
		// ... or a URL to fetch from client-side (e.g. inline on action-plan pages).
		analyticsEndpoint?: string;
		showBudget?: boolean;
	}

	let { analyticsData = null, analyticsEndpoint, showBudget = true }: Props = $props();

	let fetched: AnalyticsData | null = $state(null);
	let loading = $state(!!analyticsEndpoint && !analyticsData);
	let error = $state(false);

	async function fetchAnalytics() {
		if (!analyticsEndpoint) return;
		loading = true;
		error = false;
		try {
			const res = await fetch(analyticsEndpoint);
			if (!res.ok) {
				error = true;
				return;
			}
			fetched = await res.json();
		} catch {
			error = true;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		// Re-fetch when the endpoint changes (filter changes)
		void analyticsEndpoint;
		if (analyticsEndpoint) {
			fetchAnalytics();
		}
	});

	let data = $derived(analyticsData ?? fetched);

	// Donut palettes — stable per dimension so colors don't shuffle across reloads
	const statusColors = [
		'#94a3b8',
		'#3b82f6',
		'#f59e0b',
		'#22c55e',
		'#f97316',
		'#6b7280',
		'#a3a3a3'
	];
	const priorityColors = ['#dc2626', '#ea580c', '#eab308', '#22c55e', '#94a3b8'];
	const categoryColors = [
		'#6366f1',
		'#0ea5e9',
		'#14b8a6',
		'#84cc16',
		'#facc15',
		'#f97316',
		'#ec4899',
		'#a855f7'
	];
	const csfColors = ['#FAE482', '#85C4EA', '#B29BBA', '#F7B189', '#A8D9A0', '#9ca3af'];

	const etaLabelMap: Record<string, () => string> = {
		overdue: () => m.overdue(),
		due_30d: () => m.dueIn30Days(),
		due_90d: () => m.dueIn90Days(),
		later: () => m.laterDue(),
		no_eta: () => m.noEtaSet()
	};

	const etaColors: Record<string, string> = {
		overdue: '#dc2626',
		due_30d: '#f97316',
		due_90d: '#eab308',
		later: '#22c55e',
		no_eta: '#94a3b8'
	};

	function toDonutValues<T extends { key?: string; count: number }>(
		buckets: T[],
		labelField: keyof T
	) {
		return buckets.map((b) => {
			// Try the raw enum key first (e.g. "in_progress" → "inProgress"), then the
			// display label (e.g. "In progress"). safeTranslate falls back to its input
			// when nothing matches, so we treat that as "no translation found".
			const rawLabel = String(b[labelField] ?? '');
			const key = b.key ?? '';
			let name = rawLabel || key;
			for (const candidate of [key, rawLabel]) {
				if (!candidate) continue;
				const translated = safeTranslate(candidate);
				if (translated && translated !== candidate) {
					name = translated;
					break;
				}
			}
			return { name, value: b.count };
		});
	}

	let statusValues = $derived(data ? toDonutValues(data.by_status, 'status') : []);
	let priorityValues = $derived(data ? toDonutValues(data.by_priority, 'priority') : []);
	let categoryValues = $derived(data ? toDonutValues(data.by_category, 'category') : []);
	let csfValues = $derived(data ? toDonutValues(data.by_csf_function, 'csf_function') : []);

	let etaBars = $derived.by(() => {
		if (!data?.eta_buckets) return { labels: [] as string[], values: [] as number[] };
		const ordered = ['overdue', 'due_30d', 'due_90d', 'later', 'no_eta'];
		const map = new Map(data.eta_buckets.map((b) => [b.key, b]));
		const labels: string[] = [];
		const values: number[] = [];
		for (const k of ordered) {
			const b = map.get(k);
			if (!b) continue;
			labels.push(etaLabelMap[k]?.() ?? k);
			values.push(b.count);
		}
		return { labels, values };
	});

	let hasAnyData = $derived(!!data && data.count > 0);
</script>

{#if loading}
	<div class="bg-white p-6 shadow-sm rounded-lg">
		<div class="animate-pulse space-y-4">
			<div class="h-5 bg-gray-200 rounded w-1/4"></div>
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
				<div class="h-20 bg-gray-100 rounded-lg"></div>
				<div class="h-20 bg-gray-100 rounded-lg"></div>
				<div class="h-20 bg-gray-100 rounded-lg"></div>
			</div>
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<div class="h-64 bg-gray-100 rounded-lg"></div>
				<div class="h-64 bg-gray-100 rounded-lg"></div>
			</div>
		</div>
	</div>
{:else if error}
	<div class="bg-white p-6 shadow-sm rounded-lg">
		<p class="text-sm text-rose-600">{m.noAnalyticsData()}</p>
	</div>
{:else if !hasAnyData}
	<div class="bg-white p-6 shadow-sm rounded-lg">
		<p class="text-sm text-gray-500 italic">{m.noAnalyticsData()}</p>
	</div>
{:else if data}
	<div class="space-y-4">
		<!-- KPI row -->
		<div class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-4 gap-3">
			<SimpleCard count={String(data.count)} label={m.totalControls()} emphasis={true} />
			{#if showBudget && data.count_with_cost > 0}
				<SimpleCard
					count={data.total_annual_cost_display}
					label={m.totalAnnualCost()}
					raw={true}
				/>
				<SimpleCard
					count={`${data.count_with_cost} / ${data.count}`}
					label={m.controlsWithCostData()}
					raw={true}
				/>
			{/if}
		</div>

		<!-- ETA distribution -->
		{#if etaBars.labels.length > 0}
			<div class="bg-white rounded-lg shadow-sm p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.etaDistribution()}</h3>
				<div class="h-64">
					<BarChart
						name="appliedControlsAnalyticsEta"
						labels={etaBars.labels}
						values={etaBars.values}
						horizontal={true}
					/>
				</div>
			</div>
		{/if}

		<!-- Dimension donuts -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			{#if statusValues.length > 0}
				<div class="bg-white rounded-lg shadow-sm p-4">
					<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.controlsByStatus()}</h3>
					<div class="h-72">
						<DonutChart
							name="appliedControlsAnalyticsStatus"
							values={statusValues}
							colors={statusColors}
						/>
					</div>
				</div>
			{/if}
			{#if priorityValues.length > 0}
				<div class="bg-white rounded-lg shadow-sm p-4">
					<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.controlsByPriority()}</h3>
					<div class="h-72">
						<DonutChart
							name="appliedControlsAnalyticsPriority"
							values={priorityValues}
							colors={priorityColors}
						/>
					</div>
				</div>
			{/if}
			{#if categoryValues.length > 0}
				<div class="bg-white rounded-lg shadow-sm p-4">
					<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.controlsByCategory()}</h3>
					<div class="h-72">
						<DonutChart
							name="appliedControlsAnalyticsCategory"
							values={categoryValues}
							colors={categoryColors}
						/>
					</div>
				</div>
			{/if}
			{#if csfValues.length > 0}
				<div class="bg-white rounded-lg shadow-sm p-4">
					<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.controlsByCsfFunction()}</h3>
					<div class="h-72">
						<DonutChart
							name="appliedControlsAnalyticsCsf"
							values={csfValues}
							colors={csfColors}
						/>
					</div>
				</div>
			{/if}
		</div>

		<!-- Top owners + top folders -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			{#if data.top_owners.length > 0}
				<div class="bg-white rounded-lg shadow-sm p-4">
					<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.topOwners()}</h3>
					<table class="w-full text-sm">
						<thead>
							<tr class="text-left text-xs text-gray-500 border-b">
								<th class="py-1">{m.owner()}</th>
								<th class="py-1 text-right">{m.count()}</th>
								{#if showBudget && data.count_with_cost > 0}
									<th class="py-1 text-right">{m.cost()}</th>
								{/if}
							</tr>
						</thead>
						<tbody>
							{#each data.top_owners as row (row.label)}
								<tr class="border-b last:border-b-0">
									<td class="py-1.5">{row.label}</td>
									<td class="py-1.5 text-right tabular-nums">{row.count}</td>
									{#if showBudget && data.count_with_cost > 0}
										<td class="py-1.5 text-right tabular-nums text-gray-600">
											{row.total_display}
										</td>
									{/if}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
			{#if data.top_folders.length > 0}
				<div class="bg-white rounded-lg shadow-sm p-4">
					<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.topDomains()}</h3>
					<table class="w-full text-sm">
						<thead>
							<tr class="text-left text-xs text-gray-500 border-b">
								<th class="py-1">{m.folder()}</th>
								<th class="py-1 text-right">{m.count()}</th>
								{#if showBudget && data.count_with_cost > 0}
									<th class="py-1 text-right">{m.cost()}</th>
								{/if}
							</tr>
						</thead>
						<tbody>
							{#each data.top_folders as row (row.label)}
								<tr class="border-b last:border-b-0">
									<td class="py-1.5">{row.label}</td>
									<td class="py-1.5 text-right tabular-nums">{row.count}</td>
									{#if showBudget && data.count_with_cost > 0}
										<td class="py-1.5 text-right tabular-nums text-gray-600">
											{row.total_display}
										</td>
									{/if}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	</div>
{/if}
