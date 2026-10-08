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

	let refreshState = $state<'idle' | 'busy' | 'queued' | 'failed'>('idle');
	async function refreshNow() {
		refreshState = 'busy';
		try {
			const res = await fetch(`/fe-api/metrology/refresh-metric-instance/${metricInstance.id}`, {
				method: 'POST'
			});
			refreshState = res.ok ? 'queued' : 'failed';
		} catch {
			refreshState = 'failed';
		}
	}

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
	{#snippet actions()}
		{#if metricInstance?.is_derived}
			<button
				type="button"
				class="btn preset-filled-primary-500 h-fit"
				onclick={refreshNow}
				disabled={refreshState === 'busy'}
				data-testid="refresh-metric-button"
			>
				<i class="fa-solid fa-rotate mr-2"></i>{m.refreshNow()}
			</button>
			{#if refreshState === 'queued'}
				<span class="text-sm text-success-600-400">{m.refreshQueued()}</span>
			{:else if refreshState === 'failed'}
				<span class="text-sm text-error-500">{m.refreshFailed()}</span>
			{/if}
		{/if}
	{/snippet}
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<!-- Current Value -->
			<div class="card p-4 bg-surface-50-950 shadow-sm">
				<h3 class="text-lg font-semibold mb-3">{m.currentValue()}</h3>
				<div class="text-3xl font-bold text-primary-600">
					{metricInstance?.current_value || 'N/A'}
				</div>
				{#if metricInstance?.is_derived}
					<p class="text-xs text-surface-500 mt-2">
						{m.derivedMetricValueHint()}
					</p>
					{#if metricInstance?.last_computation_error}
						<p class="text-xs text-error-500 mt-1">
							{m.lastComputationError()}: {metricInstance.last_computation_error}
						</p>
					{/if}
				{/if}
			</div>

			<!-- Sample Timeline Chart -->
			<div class="card p-4 bg-surface-50-950 shadow-sm">
				<h3 class="text-lg font-semibold mb-3">{m.sampleTimeline()}</h3>
				{#key samples.length}
					<MetricSampleChart {samples} {metricDefinition} height="h-80" />
				{/key}
			</div>
		</div>
	{/snippet}
</DetailView>
