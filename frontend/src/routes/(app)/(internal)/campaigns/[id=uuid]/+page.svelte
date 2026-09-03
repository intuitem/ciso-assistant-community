<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { Tooltip } from '@skeletonlabs/skeleton-svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	type Target = {
		id: string;
		label: string;
		name: string;
		progress: number;
		updated_at: string | null;
		href: string;
		secondary: string | null;
	};
	type TrendPoint = { date: string; progress: number };

	// A target untouched for this long is worth chasing regardless of its progress.
	const STALE_DAYS = 14;

	const targets = $derived((data.targets ?? []) as Target[]);
	const trend = $derived((data.dashboard?.trend ?? []) as TrendPoint[]);
	const perStatus = $derived(
		(data.dashboard?.assignments?.per_status ?? {}) as Record<string, number>
	);
	const flagged = $derived((data.dashboard?.assignments?.flagged ?? 0) as number);

	// Respondent-facing order: "changes requested" is back with the respondent.
	const ASSIGNMENT_ORDER = ['draft', 'in_progress', 'changes_requested', 'submitted', 'closed'];
	const assignmentCounts = $derived(
		ASSIGNMENT_ORDER.filter((status) => perStatus[status]).map(
			(status) => [status, perStatus[status]] as const
		)
	);

	const buckets = $derived.by(() => {
		let notStarted = 0;
		let inProgress = 0;
		let complete = 0;
		for (const target of targets) {
			const progress = target.progress ?? 0;
			if (progress <= 0) notStarted += 1;
			else if (progress >= 100) complete += 1;
			else inProgress += 1;
		}
		return { notStarted, inProgress, complete };
	});

	// Plain mean, both kinds: it measures the same thing as the bar below, where every
	// target counts once. The trend is weighted by requirement count and can differ.
	const completion = $derived(
		targets.length
			? Math.round(targets.reduce((sum, t) => sum + (t.progress ?? 0), 0) / targets.length)
			: 0
	);

	const daysSince = (iso: string | null) =>
		iso === null ? null : Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
	const stale = $derived(
		targets
			.map((target) => ({ target, days: daysSince(target.updated_at) }))
			.filter((row): row is { target: Target; days: number } => (row.days ?? 0) >= STALE_DAYS)
			.sort((a, b) => b.days - a.days)
	);

	const dueDate = $derived(data.data?.due_date ? new Date(data.data.due_date) : null);
	const daysRemaining = $derived.by(() => {
		if (!dueDate) return null;
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		return Math.round((dueDate.getTime() - today.getTime()) / 86400000);
	});

	const behind = $derived(
		[...targets].sort((a, b) => (a.progress ?? 0) - (b.progress ?? 0)).slice(0, 3)
	);
	// The cross-audit matrix already exists per framework; scope it to this campaign
	// rather than duplicating it here.
	const frameworks = $derived((data.data?.frameworks ?? []) as { id: string; str: string }[]);

	// Offered while there is anything left to start: a draft campaign, or a target
	// added to one already under way.
	const draftAssignments = $derived(perStatus['draft'] ?? 0);
	// A target nobody holds keeps "start" on offer: it is the only way to wire one
	// once the missing representative or default assignee has been added.
	const unassignedTargets = $derived((data.dashboard?.assignments?.unassigned ?? 0) as number);
	// Null counts as draft, same as the backend: the column is nullable and campaigns
	// created before it had a default carry no status at all.
	const isDraft = $derived(!data.data?.status || data.data.status === 'draft');
	const canStart = $derived(
		targets.length > 0 && (isDraft || draftAssignments > 0 || unassignedTargets > 0)
	);

	const modalStore: ModalStore = getModalStore();

	function modalStartConfirm(): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: { id: data.data.id, urlmodel: 'campaigns' },
				id: data.data.id,
				debug: false,
				URLModel: 'campaigns',
				formAction: '?/start'
			}
		};
		modalStore.trigger({
			type: 'component',
			component: modalComponent,
			title: m.confirmModalTitle(),
			body: m.sureToStartCampaign({ campaign: data.data.name })
		});
	}
	const hasSpread = $derived(
		targets.length > 1 &&
			Math.max(...targets.map((t) => t.progress ?? 0)) >
				Math.min(...targets.map((t) => t.progress ?? 0))
	);

	// Sparkline over [first sample .. max(today, due date)] so the due date is on
	// the same scale as the curve.
	const spark = $derived.by(() => {
		if (trend.length < 2) return null;
		const start = new Date(trend[0].date).getTime();
		const last = new Date(trend[trend.length - 1].date).getTime();
		const end = Math.max(last, dueDate?.getTime() ?? 0);
		const span = end - start || 1;
		const x = (t: number) => ((t - start) / span) * 100;
		return {
			points: trend
				.map((p) => `${x(new Date(p.date).getTime()).toFixed(2)},${(100 - p.progress) * 0.3}`)
				.join(' '),
			dueX: dueDate ? x(dueDate.getTime()) : null
		};
	});
</script>

<DetailView {data}>
	{#snippet widgets()}
		{#if targets.length}
			<div class="h-full flex flex-col justify-center gap-4 p-4">
				<div class="flex flex-col gap-2">
					<div class="flex flex-row items-baseline justify-between">
						<span class="text-xs uppercase tracking-wide text-surface-600-400">{m.targets()}</span>
						<span class="text-sm flex items-baseline gap-1">
							<span class="text-2xl font-semibold">{completion}%</span>
							<span class="text-xs text-surface-600-400">{m.completed()}</span>
							<Tooltip positioning={{ placement: 'left' }} openDelay={200} closeDelay={100}>
								<Tooltip.Trigger>
									<i
										class="fas fa-info-circle text-xs text-surface-600-400 hover:text-primary-500 cursor-help"
										aria-label={m.campaignCompletionHelpText()}
									></i>
								</Tooltip.Trigger>
								<Tooltip.Positioner class="z-50!">
									<Tooltip.Content
										class="card bg-surface-950-50 text-white p-3 max-w-xs shadow-xl border border-surface-700-300"
									>
										<p class="text-sm">{m.campaignCompletionHelpText()}</p>
									</Tooltip.Content>
								</Tooltip.Positioner>
							</Tooltip>
						</span>
					</div>
					<div class="flex flex-row h-3 w-full rounded-full overflow-hidden bg-surface-200-800">
						{#if buckets.complete}
							<div
								class="bg-success-500"
								style="width: {(buckets.complete / targets.length) * 100}%"
							></div>
						{/if}
						{#if buckets.inProgress}
							<div
								class="bg-primary-500"
								style="width: {(buckets.inProgress / targets.length) * 100}%"
							></div>
						{/if}
						{#if buckets.notStarted}
							<div
								class="bg-surface-400-600"
								style="width: {(buckets.notStarted / targets.length) * 100}%"
							></div>
						{/if}
					</div>
					<div class="flex flex-row flex-wrap gap-x-4 gap-y-1 text-xs">
						<span class="flex items-center gap-1">
							<span class="w-2 h-2 rounded-full bg-success-500"></span>
							{m.completed()}: {buckets.complete}
						</span>
						<span class="flex items-center gap-1">
							<span class="w-2 h-2 rounded-full bg-primary-500"></span>
							{m.inProgress()}: {buckets.inProgress}
						</span>
						<span class="flex items-center gap-1">
							<span class="w-2 h-2 rounded-full bg-surface-400-600"></span>
							{m.notStarted()}: {buckets.notStarted}
						</span>
					</div>
				</div>

				<div class="flex flex-col gap-1 border-t border-surface-200-800 pt-3">
					<div class="flex flex-row items-baseline justify-between">
						<span class="text-xs uppercase tracking-wide text-surface-600-400">
							{data.thirdParty ? m.auditReviewProgress() : m.completionTrend()}
						</span>
						{#if daysRemaining !== null}
							<span class="text-xs {daysRemaining < 0 ? 'text-error-500' : ''}">
								<span class="font-semibold" data-testid="campaign-days-remaining">
									{Math.abs(daysRemaining)}
								</span>
								{daysRemaining < 0 ? m.overdue() : m.daysRemaining()}
							</span>
						{/if}
					</div>
					{#if spark}
						<svg viewBox="0 0 100 30" preserveAspectRatio="none" class="w-full h-10">
							{#if spark.dueX !== null}
								<line
									x1={spark.dueX}
									x2={spark.dueX}
									y1="0"
									y2="30"
									class="stroke-error-500"
									stroke-width="1"
									stroke-dasharray="2 2"
									vector-effect="non-scaling-stroke"
								/>
							{/if}
							<polyline
								points={spark.points}
								fill="none"
								class="stroke-primary-500"
								stroke-width="2"
								vector-effect="non-scaling-stroke"
							/>
						</svg>
					{:else}
						<span class="text-xs text-surface-600-400">{m.noData()}</span>
					{/if}
					{#if buckets.notStarted && daysRemaining !== null && daysRemaining >= 0}
						<span class="text-xs text-warning-700-300">
							{m.notStarted()}: {buckets.notStarted} / {targets.length}
						</span>
					{/if}
				</div>

				{#if assignmentCounts.length}
					<div class="flex flex-col gap-1 border-t border-surface-200-800 pt-3">
						<span class="text-xs uppercase tracking-wide text-surface-600-400">
							{m.responses()}
						</span>
						<div class="flex flex-row flex-wrap gap-2">
							{#each assignmentCounts as [status, count] (status)}
								<span class="badge preset-tonal-secondary text-xs">
									{safeTranslate(status)}: {count}
								</span>
							{/each}
							{#if flagged}
								<span class="badge preset-tonal-warning text-xs">
									{flagged}
									{m.flaggedItems()}
								</span>
							{/if}
						</div>
					</div>
				{/if}

				{#if hasSpread}
					<div class="flex flex-col gap-1 border-t border-surface-200-800 pt-3">
						<span class="text-xs uppercase tracking-wide text-surface-600-400">
							{m.furthestBehind()}
						</span>
						{#each behind as target (target.id)}
							<a
								href={target.href}
								class="flex flex-row items-center gap-2 text-xs hover:text-primary-500"
							>
								<span class="truncate flex-1 min-w-0" title={target.name}>{target.label}</span>
								<span class="w-20 h-1.5 bg-surface-300-700 rounded-full overflow-hidden shrink-0">
									<span class="block h-full bg-primary-500" style="width: {target.progress ?? 0}%"
									></span>
								</span>
								<span class="w-8 text-right tabular-nums shrink-0">{target.progress ?? 0}%</span>
							</a>
						{/each}
					</div>
				{/if}

				{#if stale.length}
					<div class="flex flex-col gap-1 border-t border-surface-200-800 pt-3">
						<span class="text-xs uppercase tracking-wide text-surface-600-400">
							{m.staleItems()}
						</span>
						{#each stale.slice(0, 3) as row (row.target.id)}
							<a
								href={row.target.href}
								class="flex flex-row items-center gap-2 text-xs hover:text-primary-500"
							>
								<span class="truncate flex-1 min-w-0" title={row.target.name}>
									{row.target.label}
								</span>
								<span class="text-warning-700-300 shrink-0 tabular-nums">
									{m.noActivityForDays({ days: row.days })}
								</span>
							</a>
						{/each}
						{#if stale.length > 3}
							<span class="text-xs text-surface-600-400">+{stale.length - 3}</span>
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	{/snippet}
	{#snippet actions()}
		{#if canStart}
			<button
				class="btn preset-filled-primary-500 h-fit"
				onclick={modalStartConfirm}
				data-testid="start-campaign-button"
			>
				<i class="fas fa-paper-plane mr-2"></i>
				{m.startCampaign()}
			</button>
		{/if}
		{#each frameworks as framework (framework.id)}
			<a
				href="/frameworks/{framework.id}/report?campaign={data.data.id}"
				class="btn preset-filled-secondary-500 h-fit"
				data-testid="campaign-insights-button"
			>
				<i class="fa-solid fa-chart-line mr-2"></i>
				{frameworks.length > 1 ? `${m.insights()} — ${framework.str}` : m.insights()}
			</a>
		{/each}
	{/snippet}
</DetailView>
