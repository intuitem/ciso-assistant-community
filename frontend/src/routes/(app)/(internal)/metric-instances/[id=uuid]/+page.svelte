<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import MetricSampleChart from '$lib/components/Chart/MetricSampleChart.svelte';
	import { m } from '$paraglide/messages';
	import { goto, invalidate, invalidateAll, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { getModalStore } from '$lib/components/Modals/stores';
	import ComposeMetricModal from '$lib/components/Modals/ComposeMetricModal.svelte';
	import { onDestroy, onMount } from 'svelte';
	import { get } from 'svelte/store';
	import { tableRefreshers } from '$lib/utils/stores';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	const metricInstance = $derived(data.data);
	const metricDefinition = $derived(metricInstance?.metric_definition);
	const isQualitative = $derived(metricDefinition?.category === 'qualitative');
	const samples = $derived(data.samples || []);

	// Refresh now queues the computation; the worker stamps last_computed_at
	// when it is done, so the page looks again until that stamp moves, then
	// shows the new value and samples without a reload.
	const REFRESH_LOOK_MS = 1500;
	const REFRESH_LOOKS = 20;
	let refreshState = $state<'idle' | 'refreshing' | 'done' | 'slow' | 'failed'>('idle');
	let refreshRun = 0;

	function refreshSampleTables() {
		for (const [endpoint, refresh] of Object.entries(get(tableRefreshers))) {
			if (endpoint.includes('custom-metric-samples')) refresh();
		}
	}

	async function refreshNow() {
		const run = ++refreshRun;
		const before = metricInstance?.last_computed_at ?? null;
		refreshState = 'refreshing';
		try {
			const res = await fetch(`/fe-api/metrology/refresh-metric-instance/${metricInstance.id}`, {
				method: 'POST'
			});
			if (!res.ok) {
				refreshState = 'failed';
				return;
			}
		} catch {
			refreshState = 'failed';
			return;
		}
		await followComputation(run, before);
	}

	// Stamps compared as moments: the save answers in another format than the
	// page's data.
	function stamp(value: string | null | undefined): number | null {
		const time = value ? Date.parse(value) : NaN;
		return Number.isNaN(time) ? null : time;
	}

	// Until the worker's stamp moves past `before`: shared by Refresh now and
	// a saved formula, which queues the same recomputation.
	async function followComputation(run: number, before: string | null) {
		refreshState = 'refreshing';
		for (let look = 0; look < REFRESH_LOOKS; look++) {
			await new Promise((resolve) => setTimeout(resolve, REFRESH_LOOK_MS));
			// Left the page, or clicked again: this run has nothing more to do.
			if (run !== refreshRun) return;
			await invalidateAll();
			if (stamp(data.data?.last_computed_at) !== stamp(before)) {
				refreshSampleTables();
				refreshState = 'done';
				setTimeout(() => {
					if (run === refreshRun && refreshState === 'done') refreshState = 'idle';
				}, 3000);
				return;
			}
		}
		refreshState = 'slow';
	}
	onDestroy(() => {
		refreshRun++;
	});

	// Arrived from the edit page after a formula save: follow the
	// recomputation it queued, then drop the marker from the address.
	onMount(() => {
		const before = page.url.searchParams.get('recomputing');
		if (before === null) return;
		const url = new URL(page.url);
		url.searchParams.delete('recomputing');
		replaceState(url, {});
		followComputation(++refreshRun, before || null);
	});

	const modalStore = getModalStore();

	// Edit formula: the creation modal, filled in, for a formula made of
	// picked instances; any other formula is edited on its definition.
	let formulaBusy = $state(false);
	// Known when the page opens, so the button says where it leads: the modal,
	// or the definition for a formula the modal does not edit.
	let formulaComposable = $state<boolean | null>(null);
	// Asked once per metric: the page data reloads while a recomputation runs.
	let composableAskedFor = '';
	$effect(() => {
		const id = metricInstance?.id;
		if (!id || !metricInstance?.is_derived || composableAskedFor === id) return;
		composableAskedFor = id;
		formulaComposable = null;
		fetch(`/fe-api/metrology/composition/${id}`)
			.then((res) => (res.ok ? res.json() : null))
			.then((body) => {
				if (body && metricInstance?.id === id) formulaComposable = !!body.composable;
			})
			.catch(() => {});
	});
	async function editFormula() {
		formulaBusy = true;
		try {
			const res = await fetch(`/fe-api/metrology/composition/${metricInstance.id}`);
			const composition = res.ok ? await res.json() : null;
			if (!composition) {
				refreshState = 'failed';
				return;
			}
			if (!composition.composable) {
				await goto(
					`/metric-definitions/${composition.definition.id}/edit?next=${encodeURIComponent(page.url.pathname)}`
				);
				return;
			}
			modalStore.trigger({
				type: 'component',
				component: {
					ref: ComposeMetricModal,
					props: {
						instanceId: metricInstance.id,
						composition,
						onSaved: (saved: { last_computed_at?: string | null }) => {
							followComputation(++refreshRun, saved.last_computed_at ?? null);
						}
					}
				}
			});
		} finally {
			formulaBusy = false;
		}
	}

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
				class="btn preset-tonal-primary h-fit"
				onclick={editFormula}
				disabled={formulaBusy}
				data-testid="edit-formula-button"
			>
				<i
					class="fa-solid {formulaBusy
						? 'fa-spinner fa-spin'
						: formulaComposable === false
							? 'fa-arrow-up-right-from-square'
							: 'fa-square-root-variable'} mr-2"
					aria-hidden="true"
				></i>{formulaComposable === false ? m.editOnDefinition() : m.editFormula()}
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500 h-fit"
				onclick={refreshNow}
				disabled={refreshState === 'refreshing'}
				aria-busy={refreshState === 'refreshing'}
				data-testid="refresh-metric-button"
			>
				<i
					class="fa-solid fa-rotate mr-2 {refreshState === 'refreshing' ? 'fa-spin' : ''}"
					aria-hidden="true"
				></i>{refreshState === 'refreshing' ? m.refreshing() : m.refreshNow()}
			</button>
			<span class="text-sm" role="status" data-testid="refresh-metric-status">
				{#if refreshState === 'done'}
					<span class="text-success-600-400">
						<i class="fa-solid fa-check mr-1" aria-hidden="true"></i>{m.refreshDone()}
					</span>
				{:else if refreshState === 'slow'}
					<span class="text-surface-600-400">{m.refreshSlow()}</span>
				{:else if refreshState === 'failed'}
					<span class="text-error-500">{m.refreshFailed()}</span>
				{/if}
			</span>
		{/if}
	{/snippet}
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<!-- Current Value -->
			<div class="card p-4 bg-surface-50-950 shadow-sm">
				<h3 class="text-lg font-semibold mb-3">{m.currentValue()}</h3>
				<!-- Dimmed while the worker recomputes: the number is about to change. -->
				<div
					class="text-3xl font-bold text-primary-600 transition-opacity {refreshState ===
					'refreshing'
						? 'opacity-40 animate-pulse'
						: ''}"
				>
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
				<!-- A recomputation can rewrite values without changing their count. -->
				{#key `${samples.length}|${metricInstance?.last_computed_at ?? ''}`}
					<MetricSampleChart {samples} {metricDefinition} height="h-80" />
				{/key}
			</div>
		</div>
	{/snippet}
</DetailView>
