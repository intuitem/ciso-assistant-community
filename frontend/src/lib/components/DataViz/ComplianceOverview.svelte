<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RingProgress from '$lib/components/DataViz/RingProgress.svelte';
	import { getScoreHexColor } from '$lib/utils/helpers';
	import { m } from '$paraglide/messages';
	import type { ComplianceOverview } from '$lib/utils/types';

	interface Props {
		overview: ComplianceOverview | null | undefined;
		name: string;
		height?: string;
		showPercentage?: boolean;
	}

	let { overview, name, height = 'h-44', showPercentage = false }: Props = $props();

	const score = $derived(overview?.global_score);
	const scoreFloor = $derived(
		score?.score_calculation_method === 'sum' ? 0 : (score?.min_score ?? 0)
	);
	const showScore = $derived(Boolean(overview?.show_score && score && score.maturity_score >= 0));
	// Nothing to count is not a verdict: an audit whose scope holds no assessable
	// requirement would otherwise render as an empty circle.
	const showResult = $derived(
		Boolean(overview?.show_result) && (overview?.donut.values ?? []).some((s) => s.value > 0)
	);
</script>

{#if !overview}
	<div
		class="flex items-center justify-center gap-2 {height} text-sm text-surface-600-400"
		data-testid="no-questionnaire"
	>
		<i class="fa-solid fa-circle-info"></i>
		<span>{m.noQuestionnaireAttached()}</span>
	</div>
{:else if showResult || showScore}
	<div class="flex flex-col">
		<span class="block text-xs text-surface-600-400 text-center">{m.compliance()}</span>
		<div class="flex flex-row items-center justify-center gap-2 {height}">
			{#if showResult}
				<div class="flex-1 min-w-0 h-full" data-testid="compliance-donut">
					<DonutChart
						name={`${name}_compliance`}
						s_label="Result"
						orientation="horizontal"
						height="h-full"
						values={overview.donut.values}
						colors={overview.donut.values.map((slice) => slice.itemStyle.color)}
						{showPercentage}
					/>
				</div>
			{/if}
			{#if showScore}
				<div class="shrink-0 w-28 h-full" data-testid="compliance-score">
					<RingProgress
						name={`${name}_maturity`}
						value={overview.global_score.maturity_score}
						max={overview.global_score.total_max_score ?? 100}
						min={scoreFloor}
						color={getScoreHexColor(
							overview.global_score.maturity_score,
							overview.global_score.total_max_score ?? 100,
							false,
							scoreFloor
						)}
						strokeWidth={30}
						fontSize={28}
						title={m.maturity()}
					/>
				</div>
			{/if}
		</div>
	</div>
{/if}
