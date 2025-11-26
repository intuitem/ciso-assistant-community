<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import MetricSampleChart from '$lib/components/Chart/MetricSampleChart.svelte';
	import { m } from '$paraglide/messages';
	import { invalidate } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';
	import { onMount } from 'svelte';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	const metricInstance = $derived(data.data);
	const metricDefinition = $derived(metricInstance?.metric_definition);
	const isQualitative = $derived(metricDefinition?.category === 'qualitative');
	const samples = $derived(data.samples || []);

	const modalStore = getModalStore();

	// Watch for modal close and refresh data
	let previousModalCount = 0;
	onMount(() => {
		const unsubscribe = modalStore.subscribe((modals) => {
			// Only invalidate when modal is closed (going from 1+ to 0)
			if (previousModalCount > 0 && modals.length === 0) {
				invalidate('metric-instance:samples');
			}
			previousModalCount = modals.length;
		});

		return unsubscribe;
	});
</script>

<DetailView {data} {form}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<!-- Current Value -->
			<div class="card p-4 bg-white shadow-sm">
				<h3 class="text-lg font-semibold mb-3">{m.currentValue()}</h3>
				<div class="text-3xl font-bold text-primary-600">
					{metricInstance?.current_value || 'N/A'}
				</div>
			</div>

			<!-- Sample Timeline Chart -->
			<div class="card p-4 bg-white shadow-sm">
				<h3 class="text-lg font-semibold mb-3">{m.sampleTimeline()}</h3>
				{#key samples.length}
					<MetricSampleChart {samples} {metricDefinition} height="h-80" />
				{/key}
			</div>
		</div>
	{/snippet}
</DetailView>
