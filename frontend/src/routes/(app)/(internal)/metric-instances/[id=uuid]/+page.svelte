<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import MetricSampleChart from '$lib/components/Chart/MetricSampleChart.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	const metricInstance = $derived(data.data);
	const metricDefinition = $derived(metricInstance?.metric_definition);
	const isQualitative = $derived(metricDefinition?.category === 'qualitative');
	const samples = $derived(data.samples || []);
</script>

<DetailView {data} {form}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-white shadow-sm">
				<h3 class="text-lg font-semibold mb-3">{m.metricDefinition()}</h3>
				<div class="space-y-3">
					<div>
						<p class="text-xs font-medium text-gray-500">{m.name()}</p>
						<p class="text-sm font-semibold">{metricDefinition?.name || 'N/A'}</p>
					</div>
					<div>
						<p class="text-xs font-medium text-gray-500">{m.refId()}</p>
						<p class="text-sm">{metricDefinition?.ref_id || 'N/A'}</p>
					</div>
					<div>
						<p class="text-xs font-medium text-gray-500">{m.category()}</p>
						<p class="text-sm">
							{#if isQualitative}
								<span class="badge bg-purple-100 text-purple-800"
									>{m.qualitative()} ({m.level()})</span
								>
							{:else}
								<span class="badge bg-blue-100 text-blue-800"
									>{m.quantitative()} ({m.number()})</span
								>
							{/if}
						</p>
					</div>

					{#if isQualitative && metricDefinition?.choices_definition?.length > 0}
						<div>
							<p class="text-xs font-medium text-gray-500 mb-2">{m.choices()}</p>
							<div class="space-y-1">
								{#each metricDefinition.choices_definition as choice, index}
									<div class="flex items-center gap-2 text-sm">
										<span class="text-gray-400">{index + 1}.</span>
										<span class="font-medium">{choice.name}</span>
									</div>
								{/each}
							</div>
						</div>
					{:else if !isQualitative}
						<div>
							<p class="text-xs font-medium text-gray-500">{m.unit()}</p>
							<p class="text-sm">{metricDefinition?.unit?.name || 'N/A'}</p>
						</div>
					{/if}

					{#if metricDefinition?.provider}
						<div>
							<p class="text-xs font-medium text-gray-500">{m.provider()}</p>
							<p class="text-sm">{metricDefinition.provider}</p>
						</div>
					{/if}
				</div>
			</div>

			<!-- Sample Timeline Chart -->
			<div class="card p-4 bg-white shadow-sm">
				<h3 class="text-lg font-semibold mb-3">{m.sampleTimeline()}</h3>
				<MetricSampleChart {samples} {metricDefinition} height="h-80" />
			</div>
		</div>
	{/snippet}
</DetailView>
