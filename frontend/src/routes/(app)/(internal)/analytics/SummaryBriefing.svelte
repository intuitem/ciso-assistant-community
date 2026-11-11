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
			number: string;
			panel: string;
			heading: string;
			dot: string;
			divider: string;
		}
	> = {
		now: {
			label: m.briefingTierNow,
			number: 'text-error-600-400',
			panel: 'bg-error-500/[0.06] border-error-500/20',
			heading: 'text-error-700-300',
			dot: 'bg-error-500',
			divider: 'border-error-500/15'
		},
		late: {
			label: m.briefingTierLate,
			number: 'text-warning-700-300',
			panel: 'bg-warning-500/[0.08] border-warning-500/25',
			heading: 'text-warning-800-200',
			dot: 'bg-warning-500',
			divider: 'border-warning-500/20'
		},
		housekeeping: {
			label: m.briefingTierHousekeeping,
			number: 'text-surface-800-200',
			panel: 'bg-surface-100-900 border-surface-200-800',
			heading: 'text-surface-700-300',
			dot: 'bg-surface-400-600',
			divider: 'border-surface-200-800'
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

	// Hero trend: daily root snapshots, only sent to users who can see the whole organisation.
	type Point = [string, number];
	const activeSeries: Point[] = $derived(metrics.trends?.active_controls ?? []);
	const shortDate = (iso: string) =>
		new Date(iso).toLocaleDateString(getLocale(), { day: 'numeric', month: 'short' });
	const heroDelta = $derived.by(() => {
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
	// x follows the dates, so gaps between snapshots stay visible as straight runs.
	const heroChart = $derived.by(() => {
		if (activeSeries.length < 2) return null;
		const [w, h, pad] = [360, 72, 8];
		const t = activeSeries.map(([d]) => new Date(d).getTime());
		const v = activeSeries.map(([, n]) => n);
		const [t0, t1, lo, hi] = [t[0], t.at(-1)!, Math.min(...v), Math.max(...v)];
		const x = (i: number) => ((t[i] - t0) / (t1 - t0 || 1)) * w;
		const y = (n: number) => (hi === lo ? h / 2 : pad + (1 - (n - lo) / (hi - lo)) * (h - 2 * pad));
		const line = v.map((n, i) => `${x(i).toFixed(1)},${y(n).toFixed(1)}`).join(' ');
		return { line, area: `M0,${h} L${line.replaceAll(' ', ' L')} L${w},${h} Z`, w, h };
	});

	// Meters fill once on first paint; the CSS transition is skipped under reduced motion.
	let filled = $state(false);
	onMount(() => requestAnimationFrame(() => (filled = true)));
	const fill = (pct: number) => (filled ? pct : 0);
</script>

<section class="pt-3 pb-2">
	<div
		class="grid grid-cols-1 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-7 border-b border-surface-200-800 pb-6"
	>
		<a href="/applied-controls/?status=active" class="hero">
			<span class="flex items-start justify-between gap-3 px-5 pt-5">
				<span>
					<span class="block text-[13px] text-surface-600-400">{m.briefingActiveControls()}</span>
					<span class="mt-1.5 flex flex-wrap items-baseline gap-x-2.5">
						<span class="hero-number"
							><AnimatedNumber value={metrics.controls?.active ?? 0} countUp /><span
								class="hero-tint"
								aria-hidden="true"
							></span></span
						>
						<span class="text-[15px] text-surface-600-400"
							>{m.briefingOfAppliedControls({ total: fmt(metrics.controls?.total) })}</span
						>
					</span>
				</span>
				{#if heroDelta}
					<span
						class="shrink-0 rounded-full bg-primary-500/10 px-2.5 py-1 text-[13px] font-semibold tabular-nums text-primary-700-300"
						>{heroDelta}</span
					>
				{/if}
			</span>
			{#if heroChart}
				<svg
					viewBox="0 0 {heroChart.w} {heroChart.h}"
					preserveAspectRatio="none"
					class="mt-3 block h-[72px] w-full"
					aria-hidden="true"
				>
					<defs>
						<linearGradient id="hero-fill" x1="0" y1="0" x2="0" y2="1">
							<stop offset="0%" stop-color="#8e51ff" stop-opacity="0.26" />
							<stop offset="100%" stop-color="#8e51ff" stop-opacity="0" />
						</linearGradient>
						<linearGradient id="hero-line" x1="0" y1="0" x2="1" y2="0">
							<stop offset="0%" stop-color="#f6339a" />
							<stop offset="100%" stop-color="#8e51ff" />
						</linearGradient>
					</defs>
					<path d={heroChart.area} fill="url(#hero-fill)" />
					<polyline
						points={heroChart.line}
						fill="none"
						stroke="url(#hero-line)"
						stroke-width="2.25"
						stroke-linejoin="round"
						vector-effect="non-scaling-stroke"
					/>
				</svg>
				<span class="flex justify-between px-5 pt-1 pb-2.5 text-[11px] text-surface-600-400">
					<span>{shortDate(activeSeries[0][0])}</span>
					<span>{shortDate(activeSeries.at(-1)![0])}</span>
				</span>
			{:else}
				<span class="block pb-5"></span>
			{/if}
		</a>

		<dl class="flex flex-col justify-between gap-3">
			<div class="stat-row">
				<dt class="text-[13px] text-surface-600-400">
					{m.sumpageAvgProgress()}
					<span class="block mt-0.5 text-xs"
						>{m.briefingAcrossAudits({ count: fmt(metrics.compliance?.active_audits) })}</span
					>
				</dt>
				<dd>
					{#await auditsMetrics}
						<span class="stat-number text-surface-400">–</span>
					{:then a}
						<a href="/compliance-assessments/" class="stat-number stat-link"
							><AnimatedNumber
								value={(a?.progress_avg ?? 0) / 100}
								format={{ style: 'percent' }}
								countUp
							/></a
						>
					{:catch}
						<span class="stat-number">–</span>
					{/await}
				</dd>
			</div>
			<div class="stat-row">
				<dt class="text-[13px] text-surface-600-400">{m.sumpageNonCompliantItems()}</dt>
				<dd>
					<a href="/requirement-assessments?result=non_compliant" class="stat-number stat-link"
						><AnimatedNumber value={metrics.compliance?.non_compliant_items ?? 0} countUp /></a
					>
				</dd>
			</div>
			<div class="stat-row last">
				<dt class="text-[13px] text-surface-600-400">
					{m.riskScenarios()}
					<span class="block mt-0.5 text-xs"
						>{m.briefingInAssessments({ count: fmt(metrics.risk?.assessments) })}</span
					>
				</dt>
				<dd>
					<a href="/risk-scenarios/" class="stat-number stat-link"
						><AnimatedNumber value={scenarios} countUp /></a
					>
				</dd>
			</div>
		</dl>
	</div>

	<div
		class="mt-8 grid grid-cols-1 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-x-12 gap-y-10 items-start"
	>
		<div>
			<h3 class="text-[15px] font-semibold mb-3">{m.briefingNeedsAttention()}</h3>
			{#if groups.length}
				<div class="space-y-2.5">
					{#each groups as group (group.tier)}
						{@const style = tierStyle[group.tier]}
						<div class="rounded-xl border px-3.5 pt-2.5 pb-1 {style.panel}">
							<p class="flex items-center gap-2 pb-1 text-[13px] font-semibold {style.heading}">
								<span class="size-2 rounded-full {style.dot}" aria-hidden="true"></span>
								{style.label()}
							</p>
							<ul>
								{#each group.items as item, i (item.label)}
									<li class={i > 0 ? `border-t ${style.divider}` : ''}>
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
	.stat-link:focus-visible,
	.hero:focus-visible {
		outline: 2px solid var(--color-primary-500);
		outline-offset: 2px;
	}
	.hero {
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border-radius: 0.875rem;
		border: 1px solid var(--color-primary-100);
		background: white;
		transition: border-color 150ms;
	}
	.hero:hover {
		border-color: var(--color-primary-300);
	}
	:global(.dark) .hero {
		border-color: var(--color-primary-900);
		background: var(--color-surface-900);
	}
	:global(.dark) .hero:hover {
		border-color: var(--color-primary-700);
	}
	/* The brand gradient of the page title, spent on one figure only. NumberFlow renders in
	   a shadow root that background-clip:text cannot reach, so the gradient is blended over
	   solid digits instead: lighten keeps the white card white and tints the black digits. */
	.hero-number {
		position: relative;
		display: inline-block;
		font-size: 4rem;
		line-height: 0.95;
		font-weight: 700;
		letter-spacing: -0.04em;
		font-variant-numeric: tabular-nums;
		color: #000;
	}
	.hero-tint {
		position: absolute;
		inset: 0;
		pointer-events: none;
		background: linear-gradient(90deg, #f6339a, #8e51ff);
		mix-blend-mode: lighten;
	}
	:global(.dark) .hero-number {
		color: #fff;
	}
	:global(.dark) .hero-tint {
		mix-blend-mode: darken;
	}
	.stat-row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--color-surface-200);
	}
	:global(.dark) .stat-row {
		border-color: var(--color-surface-800);
	}
	.stat-row.last {
		border-bottom: 0;
		padding-bottom: 0;
	}
	.stat-number {
		font-size: 1.75rem;
		line-height: 1;
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}
	.stat-link {
		border-radius: 0.25rem;
	}
	.stat-link:hover {
		text-decoration: underline;
		text-decoration-thickness: 2px;
		text-underline-offset: 4px;
	}
</style>
