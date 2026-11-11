<script lang="ts">
	import { onMount } from 'svelte';
	import { complianceResultColorMap } from '#lib/utils/constants.js';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import AnimatedNumber from '#lib/components/utils/AnimatedNumber.svelte';

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
	const fmt = (n: number | undefined) => (n ?? 0).toLocaleString(getLocale());

	type Tier = 'now' | 'late' | 'housekeeping';
	type Item = {
		tier: Tier;
		count: number;
		label: string;
		hint: string;
		href: string;
		show?: boolean;
		secondary?: { label: string; href: string };
	};

	// Listed most urgent first.
	let attention: Item[] = $derived(
		(
			[
				featureflags.incidents !== false && {
					tier: 'now',
					count: metrics.operations?.open_incidents,
					label: m.openIncidents(),
					hint: m.briefingOpenIncidentsHint(),
					href: '/incidents?status=new&status=ongoing&status=resolved'
				},
				{
					tier: 'now',
					count: metrics.controls?.eta_missed,
					label: m.sumpageEtaMissed(),
					hint: m.briefingEtaMissedHint(),
					href: `/applied-controls/?status=to_do&status=deprecated&status=in_progress&status=--&status=on_hold&eta__lte=${today}`
				},
				{
					tier: 'now',
					count: metrics.controls?.p1,
					label: m.sumpageP1(),
					hint: m.briefingP1Hint(),
					href: '/applied-controls/?priority=1&status=to_do&status=deprecated&status=degraded&status=on_hold&status=in_progress&status=--'
				},
				featureflags.tasks !== false && {
					tier: 'late',
					count: metrics.operations?.overdue_tasks,
					label: m.briefingOverdueTasks(),
					hint: m.briefingOverdueTasksHint(),
					href: `/task-nodes?past=true&status=pending&status=in_progress&due_date__gte=${overdueSince}`,
					show: metrics.operations?.overdue_tasks_total > 0,
					secondary: {
						label: m.briefingOverdueTasksTotal({
							count: fmt(metrics.operations?.overdue_tasks_total)
						}),
						href: '/task-nodes?past=true&status=pending&status=in_progress'
					}
				},
				featureflags.follow_up !== false && {
					tier: 'late',
					count: metrics.operations?.open_findings,
					label: m.briefingOpenFindings(),
					hint: m.briefingOpenFindingsHint(),
					href: '/findings?status=--&status=identified&status=confirmed&status=assigned&status=in_progress'
				},
				{
					tier: 'late',
					count: metrics.compliance?.expired_evidences,
					label: m.sumpageExpiredEvidences(),
					hint: m.briefingExpiredEvidencesHint(),
					href: '/evidences/?status=expired'
				},
				{
					tier: 'housekeeping',
					count: metrics.controls?.no_status,
					label: m.briefingControlsWithoutStatus(),
					hint: m.briefingControlsWithoutStatusHint(),
					href: '/applied-controls/?status=--'
				},
				{
					tier: 'housekeeping',
					count: metrics.controls?.degraded,
					label: m.briefingDegradedControls(),
					hint: m.briefingDegradedControlsHint(),
					href: '/applied-controls/?status=degraded'
				}
			] as (Item | false)[]
		).filter((i): i is Item => i !== false && (i.show ?? i.count > 0))
	);

	const tierStyle: Record<
		Tier,
		{
			label: () => string;
			icon: string;
			number: string;
			card: string;
			band: string;
			heading: string;
		}
	> = {
		now: {
			label: m.briefingTierNow,
			icon: 'fa-bolt',
			number: 'text-error-600-400',
			card: 'border-error-500/30',
			band: 'bg-error-500/10 border-error-500/20',
			heading: 'text-error-700-300'
		},
		late: {
			label: m.briefingTierLate,
			icon: 'fa-hourglass-half',
			number: 'text-warning-700-300',
			card: 'border-warning-500/35',
			band: 'bg-warning-500/12 border-warning-500/25',
			heading: 'text-warning-800-200'
		},
		housekeeping: {
			label: m.briefingTierHousekeeping,
			icon: 'fa-broom',
			number: 'text-surface-800-200',
			card: 'border-surface-300-700',
			band: 'bg-surface-100-900 border-surface-200-800',
			heading: 'text-surface-700-300'
		}
	};

	let groups = $derived(
		(['now', 'late', 'housekeeping'] as Tier[])
			.map((tier) => ({ tier, items: attention.filter((i) => i.tier === tier) }))
			.filter((g) => g.items.length)
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
	const share = (n: number, of: number) => (of ? Math.max((n / of) * 100, n ? 1.5 : 0) : 0);
	const highRiskRows = $derived([
		{ key: 'current', label: m.currentRisk(), count: metrics.risk?.high_current ?? 0 },
		{ key: 'residual', label: m.briefingAfterTreatment(), count: metrics.risk?.high_residual ?? 0 }
	]);

	// Trend: daily root snapshots, only sent to users who can see the whole organisation.
	type Point = [string, number];
	const activeSeries: Point[] = $derived(metrics.trends?.active_controls ?? []);
	const shortDate = (iso: string) =>
		new Date(iso).toLocaleDateString(getLocale(), { day: 'numeric', month: 'short' });
	const activeDelta = $derived.by(() => {
		if (activeSeries.length < 2) return '';
		const delta = activeSeries.at(-1)![1] - activeSeries[0][1];
		const since = shortDate(activeSeries[0][0]);
		return delta === 0
			? m.briefingNoChangeSince({ date: since })
			: m.briefingDeltaSince({
					delta: delta.toLocaleString(getLocale(), { signDisplay: 'exceptZero' }),
					date: since
				});
	});
	// Meters fill once on first paint; the CSS transition is skipped under reduced motion.
	let filled = $state(false);
	onMount(() => requestAnimationFrame(() => (filled = true)));
	const fill = (pct: number) => (filled ? pct : 0);
</script>

<section class="pt-3 pb-2">
	<dl class="grid grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-5 border-b border-surface-200-800 pb-6">
		<div>
			<dt class="text-[13px] text-surface-600-400">{m.briefingActiveControls()}</dt>
			<dd class="mt-1">
				<a href="/applied-controls/?status=active" class="stat-link">
					<span class="stat-number"
						><AnimatedNumber value={metrics.controls?.active ?? 0} countUp /></span
					>
					<span class="ml-1 text-sm text-surface-600-400"
						>{m.briefingOfAppliedControls({ total: fmt(metrics.controls?.total) })}</span
					>
				</a>
				{#if activeDelta}
					<span
						class="mt-2.5 inline-block rounded-full bg-primary-500/10 px-2 py-0.5 text-xs font-semibold tabular-nums text-primary-700-300"
						>{activeDelta}</span
					>
				{:else}
					<span class="meter" aria-hidden="true"
						><span
							style="width: {fill(
								share(metrics.controls?.active ?? 0, metrics.controls?.total ?? 0)
							)}%"
						></span></span
					>
				{/if}
			</dd>
		</div>
		<div>
			<dt class="text-[13px] text-surface-600-400">{m.sumpageAvgProgress()}</dt>
			<dd class="mt-1">
				{#await auditsMetrics}
					<span class="stat-number text-surface-400">–</span>
				{:then a}
					<a href="/compliance-assessments/" class="stat-link">
						<span class="stat-number"
							><AnimatedNumber
								value={(a?.progress_avg ?? 0) / 100}
								format={{ style: 'percent' }}
								countUp
							/></span
						>
						<span class="ml-1 text-sm text-surface-600-400"
							>{m.briefingAcrossAudits({ count: fmt(metrics.compliance?.active_audits) })}</span
						>
					</a>
					<span class="meter" aria-hidden="true"
						><span style="width: {fill(a?.progress_avg ?? 0)}%"></span></span
					>
				{:catch}
					<span class="stat-number">–</span>
				{/await}
			</dd>
		</div>
		<div>
			<dt class="text-[13px] text-surface-600-400">{m.sumpageNonCompliantItems()}</dt>
			<dd class="mt-1">
				<a href="/requirement-assessments?result=non_compliant" class="stat-link">
					<span class="stat-number"
						><AnimatedNumber value={metrics.compliance?.non_compliant_items ?? 0} countUp /></span
					>
				</a>
			</dd>
		</div>
		<div>
			<dt class="text-[13px] text-surface-600-400">{m.riskScenarios()}</dt>
			<dd class="mt-1">
				<a href="/risk-scenarios/" class="stat-link">
					<span class="stat-number"><AnimatedNumber value={scenarios} countUp /></span>
					<span class="ml-1 text-sm text-surface-600-400"
						>{m.briefingInAssessments({ count: fmt(metrics.risk?.assessments) })}</span
					>
				</a>
			</dd>
		</div>
	</dl>

	<div
		class="mt-8 grid grid-cols-1 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-x-12 gap-y-10 items-start"
	>
		<div>
			<h3 class="text-[15px] font-semibold mb-3">{m.briefingNeedsAttention()}</h3>
			{#if groups.length}
				<div class="space-y-3">
					{#each groups as group (group.tier)}
						{@const style = tierStyle[group.tier]}
						<div class="tier-card overflow-hidden rounded-xl border {style.card}">
							<p
								class="flex items-center gap-2 border-b px-4 py-2 text-[13px] font-semibold {style.band} {style.heading}"
							>
								<i class="fa-solid {style.icon} text-xs" aria-hidden="true"></i>
								{style.label()}
							</p>
							<ul class="px-3.5 py-1">
								{#each group.items as item, i (item.label)}
									<li class={i > 0 ? 'border-t border-surface-100-900' : ''}>
										<a href={item.href} class="row group">
											<span
												class="text-right text-[1.375rem] leading-none font-semibold tabular-nums {style.number}"
												>{fmt(item.count)}</span
											>
											<span class="min-w-0">
												<span class="block font-medium text-surface-950-50">{item.label}</span>
												<span class="block text-[13px] text-surface-600-400 mt-0.5"
													>{item.hint}</span
												>
											</span>
											<i
												class="fa-solid fa-chevron-right text-xs text-surface-400-600 transition-colors group-hover:text-primary-600-400 group-focus-visible:text-primary-600-400"
												aria-hidden="true"
											></i>
										</a>
										{#if item.secondary}
											<a
												href={item.secondary.href}
												class="ml-[4rem] -mt-1 mb-2 inline-block text-[13px] text-primary-700-300 underline decoration-primary-300-700 underline-offset-2 hover:decoration-current"
												>{item.secondary.label}</a
											>
										{/if}
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-surface-600-400">{m.briefingAllClear()}</p>
			{/if}
		</div>

		<aside class="space-y-9 xl:border-l xl:border-surface-200-800 xl:pl-10">
			<div>
				<div class="flex items-baseline justify-between mb-3">
					<h3 class="text-[15px] font-semibold">{m.recentlyUpdatedAudits()}</h3>
					<a
						href="/analytics?tab=compliance"
						class="text-[13px] text-primary-700-300 hover:underline">{m.viewAll()}</a
					>
				</div>
				{#await auditsMetrics}
					<div class="h-36 rounded-md bg-surface-100-900"></div>
				{:then a}
					{@const rows = auditRows(a?.audits_stats)}
					{#if rows.length}
						<ul class="space-y-3.5 text-sm">
							{#each rows as row (row.id)}
								<li>
									<a href="/compliance-assessments/{row.id}" class="block group">
										<span class="flex justify-between gap-3 mb-1.5">
											<span class="truncate group-hover:underline">{row.name}</span>
											<span class="tabular-nums text-surface-600-400 shrink-0"
												>{m.briefingAssessedPct({ pct: row.assessed })}</span
											>
										</span>
										<span class="flex h-1.5 rounded-full overflow-hidden bg-surface-200-800">
											{#each row.segments as s (s.key)}
												<span style="width: {s.pct}%; background: {complianceResultColorMap[s.key]}"
												></span>
											{/each}
										</span>
									</a>
								</li>
							{/each}
						</ul>
						<ul class="flex flex-wrap gap-x-3 gap-y-1 mt-3 text-xs text-surface-600-400">
							{#each results as key, j (key)}
								<li class="inline-flex items-center gap-1.5">
									<span
										class="size-2 rounded-full"
										style="background: {complianceResultColorMap[key]}"
									></span>{resultLabels[j]}
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-sm text-surface-600-400">{m.nothingToShowYet()}</p>
					{/if}
				{:catch}
					<p class="text-sm text-surface-600-400">–</p>
				{/await}
			</div>

			<div>
				<h3 class="text-[15px] font-semibold mb-3">{m.briefingHighRisks()}</h3>
				{#if scenarios}
					<ul class="space-y-1 text-sm">
						{#each highRiskRows as row, i (row.key)}
							<li>
								<a
									href="/risk-scenarios?top_level={row.key}"
									class="grid grid-cols-[8.5rem_minmax(0,1fr)_2.5rem] items-center gap-x-3 py-1.5 px-2 -mx-2 rounded-md hover:bg-surface-100-900 focus-visible:outline-2 focus-visible:outline-primary-500"
								>
									<span class="text-surface-700-300">{row.label}</span>
									<span class="h-2 rounded-full bg-surface-200-800 overflow-hidden"
										><span
											class="block h-full rounded-full motion-safe:transition-[width] motion-safe:duration-700 {i ===
											0
												? 'bg-error-500'
												: 'bg-warning-500'}"
											style="width: {fill(share(row.count, scenarios))}%"
										></span></span
									>
									<span class="tabular-nums text-right font-semibold">{fmt(row.count)}</span>
								</a>
							</li>
						{/each}
					</ul>
					<p class="mt-2 text-xs text-surface-600-400">
						{m.briefingHighRisksHint({ count: fmt(scenarios) })}
					</p>
				{:else}
					<p class="text-sm text-surface-600-400">{m.briefingNoScenarios()}</p>
				{/if}
			</div>
		</aside>
	</div>
</section>

<style>
	.row {
		display: grid;
		grid-template-columns: 3rem minmax(0, 1fr) auto;
		align-items: center;
		gap: 0.5rem 1rem;
		padding: 0.625rem 0.75rem 0.625rem 0.5rem;
		margin-inline: -0.5rem;
		border-radius: 0.5rem;
	}
	/* A translucent hover reads on every tier tint. */
	.row:hover {
		background: rgb(15 23 42 / 0.045);
	}
	:global(.dark) .row:hover {
		background: rgb(255 255 255 / 0.06);
	}
	.row:focus-visible,
	.stat-link:focus-visible {
		outline: 2px solid var(--color-primary-500);
		outline-offset: 2px;
	}
	.tier-card {
		background: white;
		box-shadow:
			0 1px 2px rgb(15 23 42 / 0.05),
			0 4px 12px -6px rgb(15 23 42 / 0.12);
	}
	:global(.dark) .tier-card {
		background: var(--color-surface-900);
		box-shadow: none;
	}
	.meter {
		display: block;
		margin-top: 0.625rem;
		height: 3px;
		max-width: 10rem;
		border-radius: 9999px;
		background: var(--color-surface-200);
		overflow: hidden;
	}
	:global(.dark) .meter {
		background: var(--color-surface-800);
	}
	.meter > span {
		display: block;
		height: 100%;
		border-radius: inherit;
		background: var(--color-primary-500);
	}
	@media (prefers-reduced-motion: no-preference) {
		.meter > span {
			transition: width 700ms cubic-bezier(0.2, 0.7, 0.2, 1);
		}
	}
	.stat-number {
		font-size: 1.75rem;
		line-height: 1;
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}
	.stat-link {
		display: inline-flex;
		align-items: baseline;
		border-radius: 0.25rem;
	}
	.stat-link:hover .stat-number {
		text-decoration: underline;
		text-decoration-thickness: 2px;
		text-underline-offset: 4px;
	}
</style>
