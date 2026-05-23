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
		top_owners: {
			key: string;
			label: string;
			count: number;
			total: number;
			total_display: string;
			status_breakdown: { key: string; status: string; count: number }[];
		}[];
		top_folders: {
			key: string;
			label: string;
			count: number;
			total: number;
			total_display: string;
		}[];
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
	let currentController: AbortController | null = null;

	async function fetchAnalytics() {
		if (!analyticsEndpoint) return;
		currentController?.abort();
		const controller = new AbortController();
		currentController = controller;
		loading = true;
		error = false;
		try {
			const res = await fetch(analyticsEndpoint, { signal: controller.signal });
			if (!res.ok) {
				if (currentController === controller) error = true;
				return;
			}
			const json = await res.json();
			if (currentController === controller) fetched = json;
		} catch (e) {
			if ((e as DOMException)?.name !== 'AbortError' && currentController === controller) {
				error = true;
			}
		} finally {
			if (currentController === controller) loading = false;
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
	// Match the palette used by NightingaleChart on the analytics page so CSF colors
	// stay consistent across the app. Keys are matched case-insensitively against the
	// raw enum (e.g. "govern") or its display label (e.g. "Govern").
	const csfColorMap: Record<string, string> = {
		govern: '#FAE482',
		identify: '#85C4EA',
		protect: '#B29BBA',
		detect: '#FAB647',
		respond: '#E47677',
		recover: '#8ACB93',
		_unset: '#505372'
	};
	const csfFallbackColor = '#505372';

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

	// Colors aligned to csfValues order so each segment gets its CSF-specific color
	// regardless of which functions are present and in what order.
	let csfColorsOrdered = $derived.by(() => {
		if (!data) return [] as string[];
		return data.by_csf_function.map((b) => {
			const candidates = [b.key, b.csf_function].filter(Boolean) as string[];
			for (const c of candidates) {
				const hit = csfColorMap[c.toLowerCase()];
				if (hit) return hit;
			}
			return csfFallbackColor;
		});
	});

	// Map status key → color, reusing the same palette as the by_status donut so the
	// inline owner breakdown bar uses consistent colors across the page.
	let statusColorByKey = $derived.by(() => {
		const map: Record<string, string> = {};
		if (!data) return map;
		data.by_status.forEach((b, i) => {
			if (b.key) map[b.key] = statusColors[i % statusColors.length];
		});
		return map;
	});

	function translateStatus(key: string, fallback: string) {
		if (key) {
			const translated = safeTranslate(key);
			if (translated && translated !== key) return translated;
		}
		if (fallback) {
			const translated = safeTranslate(fallback);
			if (translated && translated !== fallback) return translated;
		}
		return fallback || key;
	}

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
		<p class="text-sm text-rose-600">{m.errorLoadingData()}</p>
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
				<SimpleCard count={data.total_annual_cost_display} label={m.totalAnnualCost()} raw={true} />
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
							showPercentage={true}
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
							showPercentage={true}
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
							showPercentage={true}
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
							colors={csfColorsOrdered}
							showPercentage={true}
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
					<div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-600 mb-3">
						{#each data.by_status as s (s.key ?? s.status)}
							<div class="flex items-center gap-1.5">
								<span
									class="inline-block h-2.5 w-2.5 rounded-sm"
									style="background-color: {statusColorByKey[s.key ?? ''] ?? '#94a3b8'};"
								></span>
								<span>{translateStatus(s.key ?? '', s.status)}</span>
							</div>
						{/each}
					</div>
					<table class="w-full text-sm">
						<thead>
							<tr class="text-left text-xs text-gray-500 border-b">
								<th class="py-1">{m.owner()}</th>
								<th class="py-1">{m.controlsByStatus()}</th>
								<th class="py-1 text-right">{m.count()}</th>
								{#if showBudget && data.count_with_cost > 0}
									<th class="py-1 text-right">{m.cost()}</th>
								{/if}
							</tr>
						</thead>
						<tbody>
							{#each data.top_owners as row (row.key)}
								<tr class="border-b last:border-b-0">
									<td class="py-1.5">{row.label}</td>
									<td class="py-1.5 w-1/3">
										<div class="flex h-2 w-full rounded bg-gray-100">
											{#each row.status_breakdown as seg (seg.key)}
												{@const pct = (seg.count / row.count) * 100}
												{@const color = statusColorByKey[seg.key] ?? '#94a3b8'}
												{@const label = translateStatus(seg.key, seg.status)}
												<div
													class="relative h-full group first:rounded-l last:rounded-r"
													style="width: {pct}%; background-color: {color};"
												>
													<div
														class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 text-xs whitespace-nowrap bg-gray-900 text-white rounded opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-10 shadow"
													>
														{label}: {seg.count}
													</div>
												</div>
											{/each}
										</div>
									</td>
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
							{#each data.top_folders as row (row.key)}
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
