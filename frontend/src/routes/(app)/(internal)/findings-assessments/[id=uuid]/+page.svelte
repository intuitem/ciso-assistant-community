<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet actions()}
		<div  class="flex flex-col space-y-2">
			<Anchor
				href={`${$page.url.pathname}/action-plan`}
				class="btn variant-filled-primary h-fit"
				breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2"></i>{m.actionPlan()}</Anchor
			>
		</div>
	{/snippet}

	{#snippet widgets()}
		<div  class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-gray-50 shadow-sm">
				<h3 class="text-lg font-semibold mb-2">{m.summary()}</h3>
				<div class="grid grid-cols-2 gap-2">
					<div class="rounded-lg bg-primary-100 p-3 text-center">
						<p class="text-xs font-medium text-primary-800">Total</p>
						<p class="text-xl font-bold text-primary-900">
							{data.findings_metrics.raw_metrics.total_count || 'N/A'}
						</p>
					</div>
					<div class="rounded-lg bg-primary-100 p-3 text-center">
						<p class="text-xs font-medium text-primary-800">{m.followUpUnresolvedHigh()}</p>
						<p class="text-xl font-bold text-primary-900">
							{data.findings_metrics.raw_metrics.unresolved_important_count || 'N/A'}
						</p>
					</div>
				</div>
			</div>

			<div class="card p-4 bg-gray-50 shadow-sm flex-grow">
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
