<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

{#if data.data?.is_locked}
	<div
		class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg shadow-sm mx-4 mt-4 mb-4"
	>
		<div class="flex items-center">
			<i class="fa-solid fa-lock text-yellow-600 mr-2"></i>
			<span class="font-medium">{m.lockedAssessment()}</span>
			<span class="ml-2 text-sm">{m.lockedAssessmentMessage()}</span>
		</div>
	</div>
{/if}
<DetailView {data} disableCreate={data.data?.is_locked} disableDelete={data.data?.is_locked}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<Anchor
				href={`${page.url.pathname}/action-plan`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2"></i>{m.actionPlan()}</Anchor
			>
		</div>
	{/snippet}

	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-gray-50 shadow-xs">
				<h3 class="text-lg font-semibold mb-2">{m.summary()}</h3>
				<div class="grid grid-cols-2 gap-2">
					<div class="rounded-lg bg-primary-100 p-3 text-center">
						<p class="text-xs font-medium text-primary-800">Total</p>
						<p class="text-xl font-bold text-primary-900" data-testid="summary-total">
							{data.findings_metrics.raw_metrics.total_count || 'N/A'}
						</p>
					</div>
					<div class="rounded-lg bg-primary-100 p-3 text-center">
						<p class="text-xs font-medium text-primary-800">{m.followUpUnresolvedHigh()}</p>
						<!--                                                                          hoc = high or critical -->
						<p class="text-xl font-bold text-primary-900" data-testid="summary-unresolved-hoc">
							{data.findings_metrics.raw_metrics.unresolved_important_count || 'N/A'}
						</p>
					</div>
				</div>
			</div>

			<div class="card p-4 bg-gray-50 shadow-xs grow">
				<div class="h-1/2">
					<HalfDonutChart
						name="current_h"
						title={m.severity()}
						classesContainer="flex-1 card p-4 bg-white"
						values={data.findings_metrics.severity_chart_data}
						colors={data.findings_metrics.severity_chart_data.map((object) => object.color)}
					/>
				</div>
				<div class="h-1/2">
					<DonutChart
						classesContainer="flex-1 card p-4 bg-white"
						name="f_treatment_progress"
						title={m.progress()}
						values={data.findings_metrics.status_chart_data.values}
					/>
				</div>
			</div>
		</div>
	{/snippet}
</DetailView>
