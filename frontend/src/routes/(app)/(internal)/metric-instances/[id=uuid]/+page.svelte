<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import MetricSampleChart from '$lib/components/Chart/MetricSampleChart.svelte';
	import { m } from '$paraglide/messages';
	import { invalidate, invalidateAll } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';
	import ComposeMetricModal from '$lib/components/Modals/ComposeMetricModal.svelte';
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

	// A computed metric just created is computed by the worker a moment
	// later: look again a few times rather than show N/A until a reload.
	// Counted per instance, outside the effect: each look reloads the data and
	// re-runs it, and a stopped worker must not keep the page polling.
	let looks = { id: '', count: 0 };
	$effect(() => {
		const id = metricInstance?.id;
		if (!id || !metricInstance?.is_derived || metricInstance?.last_computed_at) return;
		if (looks.id !== id) looks = { id, count: 0 };
		if (looks.count >= 10) return;
		const timer = setTimeout(() => {
			looks.count += 1;
			invalidateAll();
		}, 2000);
		return () => clearTimeout(timer);
	});

	// A formula reads quantitative instances only.
	const composable = $derived(!isQualitative && !!metricInstance?.id);
	function useInFormula() {
		modalStore.trigger({
			type: 'component',
			component: { ref: ComposeMetricModal, props: { instanceIds: [metricInstance.id] } }
		});
	}

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

<!-- A derived series is its formula's: no sample is typed in by hand. -->
<DetailView {data} {form} disableCreate={Boolean(metricInstance?.is_derived)}>
	{#snippet actions()}
		{#if composable}
			<button
				type="button"
				class="btn preset-tonal-primary h-fit"
				onclick={useInFormula}
				data-testid="use-in-formula-button"
			>
				<i class="fa-solid fa-calculator mr-2"></i>{m.useInFormula()}
			</button>
		{/if}
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
