<script lang="ts">
	import { onMount } from 'svelte';
	import { complianceResultColorMap } from '#lib/utils/constants.js';
	import { m } from '#paraglide/messages.js';
	import { getLocale } from '#paraglide/runtime.js';
	import AnimatedNumber from '#lib/components/utils/AnimatedNumber.svelte';
	import Sparkline from './Sparkline.svelte';

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
		/** Key of its daily series in `metrics.trends`. */
		trend?: string;
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
					href: '/incidents?status=new&status=ongoing&status=resolved',
					trend: 'incidents_open'
				},
				{
					tier: 'now',
					count: metrics.controls?.eta_missed,
					label: m.sumpageEtaMissed(),
					hint: m.briefingEtaMissedHint(),
					href: `/applied-controls/?status=to_do&status=deprecated&status=in_progress&status=--&status=on_hold&status=degraded&eta__lt=${today}`,
					trend: 'controls_eta_missed'
				},
				{
					tier: 'now',
					count: metrics.controls?.p1,
					label: m.sumpageP1(),
					hint: m.briefingP1Hint(),
					href: '/applied-controls/?priority=1&status=to_do&status=deprecated&status=degraded&status=on_hold&status=in_progress&status=--',
					trend: 'controls_p1_pending'
				},
				featureflags.tasks !== false && {
					tier: 'late',
					count: metrics.operations?.overdue_tasks,
					label: m.briefingOverdueTasks(),
					hint: m.briefingOverdueTasksHint(),
					href: `/task-nodes?past=true&status=pending&status=in_progress&due_date__gte=${overdueSince}`,
					trend: 'tasks_overdue_recent',
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
					href: '/findings?status=--&status=identified&status=confirmed&status=assigned&status=in_progress',
					trend: 'findings_open'
				},
				{
					tier: 'late',
					count: metrics.compliance?.expired_evidences,
					label: m.sumpageExpiredEvidences(),
					hint: m.briefingExpiredEvidencesHint(),
					href: '/evidences/?status=expired',
					trend: 'evidence_expired'
				},
				{
					tier: 'housekeeping',
					count: metrics.controls?.no_status,
					label: m.briefingControlsWithoutStatus(),
					hint: m.briefingControlsWithoutStatusHint(),
					href: '/applied-controls/?status=--',
					trend: 'controls_no_status'
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
			tile: string;
			spark: string;
		}
	> = {
		now: {
			label: m.briefingTierNow,
			icon: 'fa-bolt',
			number: 'text-error-600-400',
			card: 'border-error-500/30',
			band: 'bg-error-500/10 border-error-500/20',
			heading: 'text-error-700-300',
			tile: 'bg-error-500/10',
			spark: 'text-error-500'
		},
		late: {
			label: m.briefingTierLate,
			icon: 'fa-hourglass-half',
			number: 'text-warning-700-300',
			card: 'border-warning-500/35',
			band: 'bg-warning-500/12 border-warning-500/25',
			heading: 'text-warning-800-200',
			tile: 'bg-warning-500/15',
			spark: 'text-warning-500'
		},
		housekeeping: {
			label: m.briefingTierHousekeeping,
			icon: 'fa-broom',
			number: 'text-surface-800-200',
			card: 'border-surface-300-700',
			band: 'bg-surface-100-900 border-surface-200-800',
			heading: 'text-surface-700-300',
			tile: 'bg-surface-100-900',
			spark: 'text-surface-400-600'
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
		new Date(iso).toLocaleDateString(getLocale(), {
			day: 'numeric',
			month: 'short',
			timeZone: 'UTC'
		});
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
	// A line needs a few days of snapshots before it says anything.
	const series = (key?: string): number[] => {
		const points: Point[] = (key && metrics.trends?.[key]) || [];
		return points.length >= 3 ? points.map((p) => p[1]) : [];
	};
	const highDrop = $derived.by(() => {
		const [current, residual] = highRiskRows.map((r) => r.count);
		return current ? Math.round(((residual - current) / current) * 100) : 0;
	});
	// Meters fill once on first paint; the CSS transition is skipped under reduced motion.
	let filled = $state(false);
	onMount(() => requestAnimationFrame(() => (filled = true)));
	const fill = (pct: number) => (filled ? pct : 0);
</script>

<section class="pt-3 pb-2">
	<dl class="strip grid grid-cols-2 lg:grid-cols-4 rounded-2xl border border-primary-500/15">
		<div class="stat">
			<dt>{m.briefingActiveControls()}</dt>
			<dd>
				<a href="/applied-controls/?status=active" class="stat-link">
					<span class="stat-number"
						><AnimatedNumber value={metrics.controls?.active ?? 0} countUp /></span
					>
					<span class="stat-context"
						>{m.briefingOfAppliedControls({ total: fmt(metrics.controls?.total) })}</span
					>
				</a>
				<span class="stat-foot">
					{#if series('active_controls').length}
						<Sparkline values={series('active_controls')} class="text-primary-500" />
					{:else}
						<span class="meter" aria-hidden="true"
							><span
								style="width: {fill(
									share(metrics.controls?.active ?? 0, metrics.controls?.total ?? 0)
								)}%"
							></span></span
						>
					{/if}
					{#if activeDelta}
						<span
							class="whitespace-nowrap rounded-full bg-primary-500/12 px-2 py-0.5 text-xs font-semibold tabular-nums text-primary-700-300"
							>{activeDelta}</span
						>
					{/if}
				</span>
			</dd>
		</div>
		<div class="stat">
			<dt>{m.sumpageAvgProgress()}</dt>
			<dd>
				{#await auditsMetrics}
					<span class="stat-number text-surface-400">–</span>
				{:then a}
					<a href="/compliance-assessments/" class="stat-link flex-row! items-center! gap-3">
						<svg viewBox="0 0 44 44" class="gauge size-11 shrink-0 -rotate-90" aria-hidden="true">
							<circle cx="22" cy="22" r="18" pathLength="100" class="gauge-track" />
							<circle
								cx="22"
								cy="22"
								r="18"
								pathLength="100"
								class="gauge-value"
								style="stroke-dashoffset: {100 - fill(a?.progress_avg ?? 0)}"
							/>
						</svg>
						<span>
							<span class="stat-number block"
								><AnimatedNumber
									value={(a?.progress_avg ?? 0) / 100}
									format={{ style: 'percent' }}
									countUp
								/></span
							>
							<span class="stat-context"
								>{m.briefingAcrossAudits({ count: fmt(metrics.compliance?.active_audits) })}</span
							>
						</span>
					</a>
					{#if series('audits_avg_assessed').length}
						<span class="stat-foot"
							><Sparkline values={series('audits_avg_assessed')} class="text-primary-500" /></span
						>
					{/if}
				{:catch}
					<span class="stat-number">–</span>
				{/await}
			</dd>
		</div>
		<div class="stat">
			<dt>{m.sumpageNonCompliantItems()}</dt>
			<dd>
				<a href="/requirement-assessments?result=non_compliant" class="stat-link">
					<span class="stat-number"
						><AnimatedNumber value={metrics.compliance?.non_compliant_items ?? 0} countUp /></span
					>
					<span class="stat-context"
						>{m.briefingOfAssessedRequirements({
							total: fmt(metrics.compliance?.assessed_items)
						})}</span
					>
				</a>
				<span class="stat-foot">
					{#if series('non_compliant_items').length}
						<Sparkline values={series('non_compliant_items')} class="text-error-500" />
					{:else}
						<span class="meter flex!" aria-hidden="true"
							>{#each [['non_compliant', metrics.compliance?.non_compliant_items], ['partially_compliant', metrics.compliance?.partially_compliant_items]] as [key, count] (key)}<span
									class="rounded-none!"
									style="width: {fill(
										share(count ?? 0, metrics.compliance?.assessed_items ?? 0)
									)}%; background: {complianceResultColorMap[key]}"
								></span>{/each}</span
						>
					{/if}
					{#if metrics.compliance?.partially_compliant_items}
						<a
							href="/requirement-assessments?result=partially_compliant"
							class="whitespace-nowrap rounded-full bg-warning-500/15 px-2 py-0.5 text-xs font-semibold tabular-nums text-warning-800-200 hover:bg-warning-500/25"
							>{m.briefingPartialCount({
								count: fmt(metrics.compliance.partially_compliant_items)
							})}</a
						>
					{/if}
				</span>
			</dd>
		</div>
		<div class="stat">
			<dt>{m.riskScenarios()}</dt>
			<dd>
				<a href="/risk-scenarios/" class="stat-link">
					<span class="stat-number"><AnimatedNumber value={scenarios} countUp /></span>
					<span class="stat-context"
						>{m.briefingInAssessments({ count: fmt(metrics.risk?.assessments) })}</span
					>
				</a>
				<span class="stat-foot">
					{#if series('total_risk_scenarios').length}
						<Sparkline values={series('total_risk_scenarios')} class="text-primary-500" />
					{:else}
						<span class="meter meter-error" aria-hidden="true"
							><span style="width: {fill(share(metrics.risk?.high_current ?? 0, scenarios))}%"
							></span></span
						>
					{/if}
					{#if metrics.risk?.high_current}
						<a
							href="/risk-scenarios?top_level=current"
							class="whitespace-nowrap rounded-full bg-error-500/10 px-2 py-0.5 text-xs font-semibold tabular-nums text-error-700-300 hover:bg-error-500/20"
							>{fmt(metrics.risk.high_current)} {m.briefingHighRisks()}</a
						>
					{/if}
				</span>
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
												class="count-tile text-[1.25rem] leading-none font-bold tabular-nums {style.tile} {style.number}"
												>{fmt(item.count)}</span
											>
											<span class="min-w-0">
												<span class="block font-medium text-surface-950-50">{item.label}</span>
												<span class="block text-[13px] text-surface-600-400 mt-0.5"
													>{item.hint}</span
												>
											</span>
											<span class="hidden sm:block">
												{#if series(item.trend).length}
													<Sparkline
														values={series(item.trend)}
														width={72}
														height={24}
														class={style.spark}
													/>
												{/if}
											</span>
											<i
												class="fa-solid fa-chevron-right text-xs text-surface-400-600 transition-colors group-hover:text-primary-600-400 group-focus-visible:text-primary-600-400"
												aria-hidden="true"
											></i>
										</a>
										{#if item.secondary}
											<a
												href={item.secondary.href}
												class="ml-[4.75rem] -mt-1 mb-2 inline-block text-[13px] text-primary-700-300 underline decoration-primary-300-700 underline-offset-2 hover:decoration-current"
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
					<div class="flex items-stretch gap-2">
						{#each highRiskRows as row, i (row.key)}
							{#if i}
								<span class="flex flex-col items-center justify-center px-1 text-surface-400-600">
									<i class="fa-solid fa-arrow-right rtl:rotate-180 text-sm" aria-hidden="true"></i>
									{#if highDrop < 0}
										<span
											class="mt-1 rounded-full bg-success-500/12 px-1.5 py-0.5 text-[11px] font-semibold tabular-nums text-success-700-300"
											>{(highDrop / 100).toLocaleString(getLocale(), {
												style: 'percent',
												signDisplay: 'exceptZero'
											})}</span
										>
									{/if}
								</span>
							{/if}
							<a
								href="/risk-scenarios?top_level={row.key}"
								class="risk-box flex-1 rounded-xl border px-3.5 py-3 {i === 0
									? 'border-error-500/25 bg-error-500/8'
									: 'border-warning-500/30 bg-warning-500/10'}"
							>
								<span class="block text-[13px] text-surface-700-300">{row.label}</span>
								<span
									class="mt-1 block text-[2rem] leading-none font-bold tabular-nums tracking-tight {i ===
									0
										? 'text-error-600-400'
										: 'text-warning-700-300'}"><AnimatedNumber value={row.count} countUp /></span
								>
								<span class="mt-2.5 block h-1.5 rounded-full bg-surface-50-950/70 overflow-hidden"
									><span
										class="block h-full rounded-full motion-safe:transition-[width] motion-safe:duration-700 {i ===
										0
											? 'bg-error-500'
											: 'bg-warning-500'}"
										style="width: {fill(share(row.count, scenarios))}%"
									></span></span
								>
							</a>
						{/each}
					</div>
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
		grid-template-columns: auto minmax(0, 1fr) auto auto;
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
	.strip {
		background:
			radial-gradient(120% 140% at 0% 0%, rgb(124 58 237 / 0.09), transparent 55%),
			radial-gradient(90% 120% at 100% 100%, rgb(79 70 229 / 0.06), transparent 60%), white;
		box-shadow: 0 1px 2px rgb(15 23 42 / 0.04);
	}
	:global(.dark) .strip {
		background:
			radial-gradient(120% 140% at 0% 0%, rgb(139 92 246 / 0.16), transparent 55%),
			var(--color-surface-900);
	}
	.stat {
		padding: 1.125rem 1.5rem 1.25rem;
	}
	.stat + .stat {
		border-inline-start: 1px solid rgb(124 58 237 / 0.12);
	}
	@media (max-width: 1023px) {
		.stat:nth-child(3) {
			border-inline-start: 0;
		}
		.stat:nth-child(n + 3) {
			border-top: 1px solid rgb(124 58 237 / 0.12);
		}
	}
	.stat dt {
		font-size: 13px;
		font-weight: 500;
		color: var(--color-surface-600);
	}
	:global(.dark) .stat dt {
		color: var(--color-surface-400);
	}
	.stat dd {
		margin-top: 0.375rem;
	}
	.stat-number {
		font-size: 2.25rem;
		line-height: 1;
		font-weight: 700;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}
	.stat-context {
		display: block;
		margin-top: 0.375rem;
		font-size: 0.875rem;
		color: var(--color-surface-600);
	}
	:global(.dark) .stat-context {
		color: var(--color-surface-400);
	}
	.stat-foot {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		margin-top: 0.75rem;
		min-height: 28px;
	}
	.meter-error > span {
		background: var(--color-error-500);
	}
	.stat-foot .meter {
		margin-top: 0;
		width: 6rem;
	}
	.stat-link {
		display: inline-flex;
		flex-direction: column;
		align-items: flex-start;
		border-radius: 0.25rem;
	}
	.stat-link:hover .stat-number {
		text-decoration: underline;
		text-decoration-thickness: 2px;
		text-underline-offset: 5px;
	}
	.gauge-track,
	.gauge-value {
		fill: none;
		stroke-width: 5;
	}
	.gauge-track {
		stroke: rgb(124 58 237 / 0.14);
	}
	.gauge-value {
		stroke: var(--color-primary-500);
		stroke-linecap: round;
		stroke-dasharray: 100;
	}
	@media (prefers-reduced-motion: no-preference) {
		.gauge-value {
			transition: stroke-dashoffset 900ms cubic-bezier(0.2, 0.7, 0.2, 1);
		}
	}
	.count-tile {
		display: grid;
		place-items: center;
		min-width: 3.75rem;
		height: 2.75rem;
		padding-inline: 0.5rem;
		border-radius: 0.625rem;
	}
	.risk-box {
		transition:
			transform 150ms ease,
			box-shadow 150ms ease;
	}
	.risk-box:hover {
		box-shadow: 0 4px 14px -6px rgb(15 23 42 / 0.2);
	}
	.risk-box:focus-visible {
		outline: 2px solid var(--color-primary-500);
		outline-offset: 2px;
	}
</style>
