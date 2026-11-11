<script lang="ts">
	import { complianceResultColorMap } from '#lib/utils/constants.js';
	import { m } from '#paraglide/messages.js';

	interface Props {
		metrics: any;
		auditsMetrics: Promise<any>;
		featureflags?: Record<string, boolean>;
	}

	let { metrics, auditsMetrics, featureflags = {} }: Props = $props();

	const isoDay = (d: Date) => d.toISOString().split('T')[0];
	const today = isoDay(new Date());
	// Matches OVERDUE_TASKS_WINDOW_DAYS in backend/core/helpers.py.
	const overdueSince = isoDay(new Date(Date.now() - 30 * 86_400_000));
	const fmt = (n: number | undefined) => (n ?? 0).toLocaleString();

	type Item = {
		count: number;
		label: string;
		hint: string;
		href: string;
		tone?: string;
		show?: boolean;
		secondary?: { label: string; href: string };
	};

	// Order is severity: what is happening now, then what is late, then hygiene.
	let attention: Item[] = $derived(
		[
			featureflags.incidents !== false && {
				count: metrics.operations?.open_incidents,
				label: m.openIncidents(),
				hint: m.briefingOpenIncidentsHint(),
				href: '/incidents?status=new&status=ongoing&status=resolved',
				tone: 'text-error-600-400'
			},
			{
				count: metrics.controls?.eta_missed,
				label: m.sumpageEtaMissed(),
				hint: m.briefingEtaMissedHint(),
				href: `/applied-controls/?status=to_do&status=deprecated&status=in_progress&status=--&status=on_hold&eta__lte=${today}`,
				tone: 'text-error-600-400'
			},
			{
				count: metrics.controls?.p1,
				label: m.sumpageP1(),
				hint: m.briefingP1Hint(),
				href: '/applied-controls/?priority=1&status=to_do&status=deprecated&status=degraded&status=on_hold&status=in_progress&status=--',
				tone: 'text-warning-700-300'
			},
			featureflags.tasks !== false && {
				count: metrics.operations?.overdue_tasks,
				label: m.briefingOverdueTasks(),
				hint: m.briefingOverdueTasksHint(),
				href: `/task-nodes?past=true&status=pending&status=in_progress&due_date__gte=${overdueSince}`,
				tone: 'text-warning-700-300',
				show: metrics.operations?.overdue_tasks_total > 0,
				secondary: {
					label: m.briefingOverdueTasksTotal({
						count: fmt(metrics.operations?.overdue_tasks_total)
					}),
					href: '/task-nodes?past=true&status=pending&status=in_progress'
				}
			},
			featureflags.follow_up !== false && {
				count: metrics.operations?.open_findings,
				label: m.briefingOpenFindings(),
				hint: m.briefingOpenFindingsHint(),
				href: '/findings?status=--&status=identified&status=confirmed&status=assigned&status=in_progress'
			},
			{
				count: metrics.compliance?.expired_evidences,
				label: m.sumpageExpiredEvidences(),
				hint: m.briefingExpiredEvidencesHint(),
				href: '/evidences/?status=expired',
				tone: 'text-warning-700-300'
			},
			{
				count: metrics.controls?.no_status,
				label: m.briefingControlsWithoutStatus(),
				hint: m.briefingControlsWithoutStatusHint(),
				href: '/applied-controls/?status=--'
			},
			{
				count: metrics.controls?.degraded,
				label: m.briefingDegradedControls(),
				hint: m.briefingDegradedControlsHint(),
				href: '/applied-controls/?status=degraded'
			}
		].filter((i): i is Item => Boolean(i) && ((i as Item).show ?? (i as Item).count > 0))
	);

	const results = [
		'not_assessed',
		'partially_compliant',
		'non_compliant',
		'compliant',
		'not_applicable'
	] as const;
	const resultLabels = $derived([
		m.notAssessed(),
		m.partiallyCompliant(),
		m.nonCompliant(),
		m.compliant(),
		m.notApplicable()
	]);

	function auditRows(stats: any) {
		if (!stats?.data?.length) return [];
		return stats.data.slice(0, 5).map((counts: number[], i: number) => {
			const total = counts.reduce((a, b) => a + b, 0) || 1;
			return {
				id: stats.uuids[i],
				name: stats.names[i],
				assessed: Math.round(((total - counts[0]) / total) * 100),
				segments: counts.map((c, j) => ({ key: results[j], pct: (c / total) * 100 }))
			};
		});
	}

	const scenarios = $derived(metrics.risk?.scenarios ?? 0);
	const highRiskRows = $derived([
		{
			key: 'current',
			label: m.currentRisk(),
			count: metrics.risk?.high_current ?? 0,
			bar: 'bg-error-500'
		},
		{
			key: 'residual',
			label: m.residualRisk(),
			count: metrics.risk?.high_residual ?? 0,
			bar: 'bg-warning-500'
		}
	]);
	const pct = (n: number) => (scenarios ? Math.max((n / scenarios) * 100, n ? 1 : 0) : 0);
</script>

<section class="space-y-8 pt-2" aria-labelledby="briefing-title">
	<h2 id="briefing-title" class="sr-only">{m.summary()}</h2>

	<dl
		class="grid grid-cols-2 lg:grid-cols-4 border-y border-surface-200-800 divide-surface-200-800 lg:divide-x"
	>
		<div class="py-4 pr-5">
			<dt class="text-sm text-surface-600-400">{m.briefingActiveControls()}</dt>
			<dd class="mt-1 text-3xl font-semibold tabular-nums tracking-tight">
				<a href="/applied-controls/?status=active" class="hover:underline"
					>{fmt(metrics.controls?.active)}</a
				><span class="ml-1.5 text-base font-normal text-surface-500">
					/ {fmt(metrics.controls?.total)}</span
				>
			</dd>
		</div>
		<div class="py-4 lg:px-5">
			<dt class="text-sm text-surface-600-400">{m.sumpageAvgProgress()}</dt>
			<dd class="mt-1 text-3xl font-semibold tabular-nums tracking-tight">
				{#await auditsMetrics}
					<span class="text-surface-400">…</span>
				{:then a}
					<a href="/compliance-assessments/" class="hover:underline">{a?.progress_avg ?? '-'}%</a>
				{:catch}
					-
				{/await}<span class="ml-1.5 text-base font-normal text-surface-500">
					· {m.briefingActiveAudits({ count: fmt(metrics.compliance?.active_audits) })}</span
				>
			</dd>
		</div>
		<div class="py-4 pr-5 lg:px-5">
			<dt class="text-sm text-surface-600-400">{m.sumpageNonCompliantItems()}</dt>
			<dd class="mt-1 text-3xl font-semibold tabular-nums tracking-tight">
				<a href="/requirement-assessments?result=non_compliant" class="hover:underline"
					>{fmt(metrics.compliance?.non_compliant_items)}</a
				>
			</dd>
		</div>
		<div class="py-4 lg:pl-5">
			<dt class="text-sm text-surface-600-400">{m.riskScenarios()}</dt>
			<dd class="mt-1 text-3xl font-semibold tabular-nums tracking-tight">
				<a href="/risk-scenarios/" class="hover:underline">{fmt(scenarios)}</a><span
					class="ml-1.5 text-base font-normal text-surface-500"
				>
					· {m.briefingAssessments({ count: fmt(metrics.risk?.assessments) })}</span
				>
			</dd>
		</div>
	</dl>

	<div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)] gap-10 items-start">
		<div>
			<div class="flex items-baseline justify-between mb-1">
				<h3 class="text-base font-semibold">{m.briefingNeedsAttention()}</h3>
				{#if attention.length}
					<span class="text-sm text-surface-500">{attention.length}</span>
				{/if}
			</div>
			{#if attention.length}
				<ul class="border-b border-surface-200-800">
					{#each attention as item (item.label)}
						<li class="border-t border-surface-200-800">
							<a
								href={item.href}
								class="group grid grid-cols-[4rem_minmax(0,1fr)_auto] items-center gap-3 py-3.5 px-1 hover:bg-surface-100-900 rounded-sm"
							>
								<span class="text-2xl font-semibold tabular-nums {item.tone ?? ''}"
									>{fmt(item.count)}</span
								>
								<span>
									<span class="block font-medium">{item.label}</span>
									<span class="block text-sm text-surface-600-400 mt-0.5">{item.hint}</span>
								</span>
								<span
									class="text-sm text-primary-600-400 opacity-70 group-hover:opacity-100"
									aria-hidden="true">{m.review()} →</span
								>
							</a>
							{#if item.secondary}
								<a
									href={item.secondary.href}
									class="block -mt-2 pb-3 pl-[4.75rem] text-sm text-primary-600-400 hover:underline"
									>{item.secondary.label} →</a
								>
							{/if}
						</li>
					{/each}
				</ul>
			{:else}
				<p class="border-y border-surface-200-800 py-6 text-surface-600-400">
					{m.briefingAllClear()}
				</p>
			{/if}
		</div>

		<div class="space-y-8">
			<div>
				<div class="flex items-baseline justify-between mb-3">
					<h3 class="text-base font-semibold">{m.recentlyUpdatedAudits()}</h3>
					<a href="/analytics?tab=compliance" class="text-sm text-primary-600-400 hover:underline"
						>{m.viewAll()} →</a
					>
				</div>
				{#await auditsMetrics}
					<div class="h-32 animate-pulse rounded bg-surface-100-900"></div>
				{:then a}
					{@const rows = auditRows(a?.audits_stats)}
					{#if rows.length}
						<ul class="space-y-3 text-sm">
							{#each rows as row (row.id)}
								<li>
									<a href="/compliance-assessments/{row.id}" class="block group">
										<span class="flex justify-between gap-3 mb-1.5">
											<span class="truncate group-hover:underline">{row.name}</span>
											<span class="tabular-nums text-surface-500 shrink-0"
												>{m.briefingAssessedPct({ pct: row.assessed })}</span
											>
										</span>
										<span class="flex h-1.5 rounded-sm overflow-hidden bg-surface-200-800">
											{#each row.segments as s (s.key)}
												<span style="width: {s.pct}%; background: {complianceResultColorMap[s.key]}"
												></span>
											{/each}
										</span>
									</a>
								</li>
							{/each}
						</ul>
						<div class="flex flex-wrap gap-x-3 gap-y-1 mt-3 text-xs text-surface-600-400">
							{#each results as key, j (key)}
								<span class="inline-flex items-center gap-1.5"
									><span
										class="size-2 rounded-xs"
										style="background: {complianceResultColorMap[key]}"
									></span>{resultLabels[j]}</span
								>
							{/each}
						</div>
					{:else}
						<p class="text-sm text-surface-600-400">{m.nothingToShowYet()}</p>
					{/if}
				{:catch}
					<p class="text-sm text-surface-600-400">-</p>
				{/await}
			</div>

			<div>
				<div class="flex items-baseline justify-between mb-3">
					<h3 class="text-base font-semibold">{m.briefingHighRisks()}</h3>
					<a
						href="/risk-scenarios?top_level=current"
						class="text-sm text-primary-600-400 hover:underline">{m.review()} →</a
					>
				</div>
				{#if scenarios}
					<ul class="space-y-1 text-sm">
						{#each highRiskRows as row (row.key)}
							<li>
								<a
									href="/risk-scenarios?top_level={row.key}"
									class="grid grid-cols-[5.5rem_minmax(0,1fr)_3rem] items-center gap-x-3 py-1 px-1 -mx-1 rounded-sm hover:bg-surface-100-900"
								>
									<span class="text-surface-600-400">{row.label}</span>
									<span class="h-3 rounded-sm bg-surface-200-800 overflow-hidden"
										><span class="block h-full {row.bar}" style="width: {pct(row.count)}%"
										></span></span
									>
									<span class="tabular-nums text-right font-medium">{fmt(row.count)}</span>
								</a>
							</li>
						{/each}
					</ul>
					<p class="mt-2.5 text-xs text-surface-600-400">
						{m.briefingHighRisksHint({ count: fmt(scenarios) })}
					</p>
				{:else}
					<p class="text-sm text-surface-600-400">{m.briefingNoScenarios()}</p>
				{/if}
			</div>
		</div>
	</div>
</section>
