<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RingProgress from '$lib/components/DataViz/RingProgress.svelte';
	import { getScoreHexColor } from '$lib/utils/helpers';
	import { m } from '$paraglide/messages';
	import type { ComplianceOverview } from '$lib/utils/types';

	interface Props {
		overview: ComplianceOverview | null | undefined;
		name: string;
	}

	let { overview, name }: Props = $props();

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
	const columns = $derived(Number(showScore) + Number(showResult));
</script>

{#if !overview}
	<div
		class="flex h-full items-center justify-center gap-2 p-2 text-sm text-surface-600-400"
		data-testid="no-questionnaire"
	>
		<i class="fa-solid fa-circle-info"></i>
		<span>{m.noQuestionnaireAttached()}</span>
	</div>
{:else if columns > 0}
	<div
		class="grid w-full gap-2"
		style="grid-template-columns: repeat({columns}, minmax(0, 1fr)); grid-auto-rows: minmax(14rem, auto);"
	>
		{#if showScore}
			<div class="min-w-0 min-h-56" data-testid="compliance-score">
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
					strokeWidth={16}
					fontSize={32}
					radius="55%"
					title={m.maturity()}
				/>
			</div>
		{/if}
		{#if showResult}
			<div class="min-w-0 min-h-56" data-testid="compliance-donut">
				<DonutChart
					name={`${name}_compliance`}
					s_label="Result"
					title={m.compliance()}
					orientation="horizontal"
					values={overview.donut.values}
					colors={overview.donut.values.map((slice) => slice.itemStyle.color)}
					showPercentage={true}
				/>
			</div>
		{/if}
	</div>
{/if}
