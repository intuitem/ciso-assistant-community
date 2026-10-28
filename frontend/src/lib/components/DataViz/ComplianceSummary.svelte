<script lang="ts">
	import { getScoreTextClass, roundScore } from '#lib/utils/helpers.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import type { ComplianceOverview } from '#lib/utils/types.js';

	interface Props {
		overview: ComplianceOverview | null | undefined;
	}

	let { overview }: Props = $props();

	const slices = $derived((overview?.donut.values ?? []).filter((slice) => slice.value > 0));
	const assessed = $derived(slices.reduce((sum, slice) => sum + slice.value, 0));
	const score = $derived(overview?.global_score);
	const scoreFloor = $derived(
		score?.score_calculation_method === 'sum' ? 0 : (score?.min_score ?? 0)
	);
	const scoreCeiling = $derived(score?.total_max_score ?? 100);
	const showScore = $derived(Boolean(overview?.show_score && score && score.maturity_score >= 0));
	const showResult = $derived(Boolean(overview?.show_result) && assessed > 0);
	const share = (value: number) => Math.round((value / assessed) * 100);
	const applicable = $derived(
		assessed - (slices.find((slice) => slice.name === 'not_applicable')?.value ?? 0)
	);
	const compliantShare = $derived(
		applicable > 0
			? Math.round(
					((slices.find((slice) => slice.name === 'compliant')?.value ?? 0) / applicable) * 100
				)
			: 0
	);
	// The tooltip's content, for readers that never see it.
	const breakdownLabel = $derived(
		`${m.compliance()}: ` +
			slices.map((slice) => `${safeTranslate(slice.localName)} ${share(slice.value)}%`).join(', ')
	);
</script>

{#if !overview}
	<div class="flex items-center gap-2 text-sm text-surface-600-400" data-testid="no-questionnaire">
		<i class="fa-solid fa-circle-info"></i>
		<span>{m.noQuestionnaireAttached()}</span>
	</div>
{:else if showResult || showScore}
	<div class="flex flex-col gap-2">
		<div class="flex items-baseline justify-between gap-2">
			<!-- With no bar under it, a Compliance label would head nothing. -->
			<span class="flex items-baseline gap-1 text-sm text-surface-600-400">
				{showResult ? m.compliance() : m.maturity()}
				{#if showResult}
					<span class="font-semibold {getScoreTextClass(compliantShare, 100)}">
						{compliantShare}%
					</span>
				{/if}
			</span>
			{#if showScore}
				<span class="flex items-baseline gap-1 text-sm" data-testid="compliance-score">
					{#if showResult}
						<span class="text-surface-600-400">{m.maturity()}</span>
					{/if}
					<span
						class="font-semibold {getScoreTextClass(
							overview.global_score.maturity_score,
							scoreCeiling,
							false,
							scoreFloor
						)}"
					>
						{roundScore(overview.global_score.maturity_score, 2)}
					</span>
					<span class="text-surface-600-400">/ {scoreCeiling}</span>
				</span>
			{/if}
		</div>
		{#if showResult}
			<div class="group relative">
				<!-- Segments grow by count, so rounding never leaves the bar short. -->
				<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
				<!-- A tab stop on purpose: it is what opens the breakdown without a mouse. -->
				<div
					class="flex h-3 w-full gap-px overflow-hidden rounded-full bg-surface-300-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
					data-testid="compliance-bar"
					tabindex="0"
					role="img"
					aria-label={breakdownLabel}
				>
					{#each slices as slice (slice.name)}
						<div style="flex: {slice.value} 1 0%; background-color: {slice.itemStyle.color}"></div>
					{/each}
				</div>
				<div
					class="absolute bottom-full left-1/2 z-10 mb-1 w-max max-w-full -translate-x-1/2 rounded bg-gray-900 px-2 py-1 text-xs text-white opacity-0 shadow transition-opacity pointer-events-none group-hover:opacity-100 group-focus-within:opacity-100"
					role="tooltip"
				>
					{#each slices as slice (slice.name)}
						<div class="flex items-center gap-2">
							<span
								class="size-2 shrink-0 rounded-full"
								style="background-color: {slice.itemStyle.color}"
							></span>
							<span>{safeTranslate(slice.localName)}</span>
							<span class="ml-auto font-semibold">{share(slice.value)}%</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
