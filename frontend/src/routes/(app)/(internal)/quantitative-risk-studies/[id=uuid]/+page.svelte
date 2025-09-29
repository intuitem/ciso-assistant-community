<script lang="ts">
	import type { ActionData, PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import LossExceedanceCurve from '$lib/components/Chart/LossExceedanceCurve.svelte';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { run } from 'svelte/legacy';
	import { getToastStore } from '$lib/components/Toast/stores.ts';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	let retriggerIsLoading = $state(false);

	const toastStore = getToastStore();

	run(() => {
		if (form?.message?.simulationsComplete) {
			// Add a small delay to ensure database transaction is committed
			setTimeout(() => {
				invalidateAll();
			}, 100);
		}
	});
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<Anchor
				href={`${page.url.pathname}/action-plan`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"
			>
				<i class="fa-solid fa-heart-pulse mr-2 capitalize"></i>{m.actionPlan()}
			</Anchor>
			<Anchor
				href={`${page.url.pathname}/executive-summary`}
				class="btn bg-emerald-500 hover:bg-emerald-600 text-white h-fit"
				breadcrumbAction="push"
			>
				<i class="fa-solid fa-chart-line mr-2"></i>{m.executiveSummary()}
			</Anchor>
			<Anchor
				href={`${page.url.pathname}/key-metrics`}
				class="btn bg-amber-500 hover:bg-amber-600 text-white h-fit"
				breadcrumbAction="push"
			>
				<i class="fa-solid fa-chart-simple mr-2"></i>{m.keyMetrics()}
			</Anchor>
			<form
				method="POST"
				action="?/retriggerAllSimulations"
				use:enhance={() => {
					retriggerIsLoading = true;
					return async ({ result, update }) => {
						await update();
						retriggerIsLoading = false;

						// Handle responses immediately in the enhance callback
						if (result.type === 'success') {
							if (result.data?.error) {
								const errorData = result.data.message;
								toastStore.trigger({
									message: `Simulation Failed: ${errorData.details || errorData.error || 'Unknown error occurred'}`,
									background: 'bg-red-400 text-white',
									timeout: 5000,
									autohide: true
								});
							} else if (result.data?.success) {
								// The server action wraps the backend response in message.results
								const backendResults = result.data.message?.results;
								const summary = backendResults?.simulation_results?.summary;

								if (backendResults?.success === false) {
									// Backend reported failure
									toastStore.trigger({
										message: `Simulation Failed: ${backendResults.message || 'Unknown error occurred'}`,
										background: 'bg-red-400 text-white',
										timeout: 5000,
										autohide: true
									});
								} else {
									// Backend reported success
									let message = 'All simulations completed successfully!';

									if (summary) {
										if (summary.failed_simulations > 0) {
											message = `Simulations completed with ${summary.failed_simulations} failures out of ${summary.total_hypotheses} hypotheses`;
										} else {
											message = `All ${summary.successful_simulations} simulations completed successfully!`;
										}
									}

									toastStore.trigger({
										message: message,
										background:
											summary?.failed_simulations > 0
												? 'bg-yellow-500 text-white'
												: 'bg-green-500 text-white',
										autohide: true,
										timeout: 4000
									});
								}
							} else {
								toastStore.trigger({
									message: 'Unexpected response format from server',
									background: 'bg-yellow-500 text-white',
									timeout: 3000,
									autohide: true
								});
							}
						} else {
							// Handle other result types (error, failure, etc.)
							toastStore.trigger({
								message: `Request failed: ${result.type}`,
								background: 'bg-red-400 text-white',
								timeout: 3000,
								autohide: true
							});
						}
					};
				}}
			>
				<button
					type="submit"
					class="btn bg-violet-500 hover:bg-violet-600 text-white h-fit disabled:opacity-50 disabled:cursor-not-allowed"
					disabled={retriggerIsLoading}
					title="Retrigger all simulations for this study including hypotheses, portfolio data, and risk tolerance curve"
				>
					<span class="mr-2">
						{#if retriggerIsLoading}
							<ProgressRing
								strokeWidth="16px"
								meterStroke="stroke-white"
								size="size-6"
								classes="-ml-2"
							/>
						{:else}
							<i class="fa-solid fa-arrows-rotate"></i>
						{/if}
					</span>
					{m.retriggerAllSimulations()}
				</button>
			</form>
		</div>
	{/snippet}

	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4 bg-slate-100 rounded-xl p-4">
			{#if data.combinedAle?.combined_metrics}
				{@const metrics = data.combinedAle.combined_metrics}
				<!-- Combined ALE Metrics -->
				<div class="bg-white rounded-lg p-6 shadow-sm">
					<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
						<!-- Current ALE Combined -->
						<div class="text-center">
							<div class="text-2xl font-bold text-blue-600 mb-2">
								{metrics.current_ale_combined_display}
							</div>
							<div class="text-sm text-gray-600">{m.currentAleCombined()}</div>
							<div class="text-xs text-gray-500 mt-1">
								{data.combinedAle.scenarios_with_current_ale} / {data.combinedAle.total_scenarios} {m.scenarios()}
							</div>
						</div>

						<!-- Residual ALE Combined -->
						<div class="text-center">
							<div class="text-2xl font-bold text-green-600 mb-2">
								{metrics.residual_ale_combined_display}
							</div>
							<div class="text-sm text-gray-600">{m.residualAleCombined()}</div>
							<div class="text-xs text-gray-500 mt-1">
								{data.combinedAle.scenarios_with_residual_ale} / {data.combinedAle.total_scenarios} {m.scenarios()}
							</div>
						</div>

						<!-- Risk Reduction -->
						<div class="text-center">
							<div class="text-2xl font-bold text-purple-600 mb-2">
								{metrics.risk_reduction_display}
							</div>
							<div class="text-sm text-gray-600">{m.riskReduction()}</div>
							<div class="text-xs text-gray-500 mt-1">{m.currentAle()} - {m.residualAle()}</div>
						</div>
					</div>

					<!-- Summary information -->
					<div class="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-600">
						<p class="text-center">
							<i class="fa-solid fa-circle-info"></i> {m.assumingIndependentScenarios()}
						</p>
					</div>
				</div>

				<!-- Combined LEC Chart Section -->
				{#if data.combinedLec?.curves && data.combinedLec.curves.length > 0}
					{@const curves = data.combinedLec.curves}
					{@const currentRiskCurve = curves.find((c) => c.type === 'combined_current')}
					{@const residualRiskCurve = curves.find((c) => c.type === 'combined_residual')}
					{@const toleranceCurve = curves.find((c) => c.type === 'tolerance')}

					<div class="bg-white rounded-lg p-6 shadow-sm">
						<div class="flex justify-between items-center mb-4">
							<h3 class="text-lg font-semibold">{m.portfolioOverview()}</h3>
							<div class="text-sm text-gray-600">
								Current: {data.combinedLec.scenarios_with_current_data} / {data.combinedLec
									.total_scenarios}
								{#if data.combinedLec.scenarios_with_residual_data}
									| Residual: {data.combinedLec.scenarios_with_residual_data} / {data.combinedLec
										.total_scenarios} {m.scenarios()}
								{/if}
							</div>
						</div>

						<div class="w-full">
							<LossExceedanceCurve
								data={currentRiskCurve?.data || []}
								residualData={residualRiskCurve?.data || []}
								toleranceData={toleranceCurve?.data || []}
								lossThreshold={data.data.loss_threshold}
								currency={data.combinedLec.currency}
								title={m.combinedStudyRiskProfile()}
								showTitle={false}
								height="h-96"
								width="w-full"
								enableTooltip={true}
								autoYMax={true}
								autoXMax={true}
								classesContainer="min-w-0"
							/>
						</div>
					</div>
				{:else}
					<!-- Empty State for LEC Chart -->
					<div class="bg-white rounded-lg p-8 shadow-sm text-center">
						<div class="flex flex-col items-center space-y-4">
							<i class="fa-solid fa-chart-area text-4xl text-gray-400"></i>
							<h5 class="text-lg font-semibold text-gray-600">{m.combinedLossExceedanceCurve()}</h5>
							<p class="text-gray-500">
								{m.noLecDataAvailable()}
							</p>
						</div>
					</div>
				{/if}
			{:else}
				<!-- Empty State -->
				<div class="bg-white rounded-lg p-8 shadow-sm text-center">
					<div class="flex flex-col items-center space-y-4">
						<i class="fa-solid fa-chart-column text-4xl text-gray-400"></i>
						<h5 class="text-lg font-semibold text-gray-600">{m.combinedAleMetrics()}</h5>
						<p class="text-gray-500">
							{m.noAleDataAvailableRunSimulations()}
						</p>
					</div>
				</div>
			{/if}
		</div>
	{/snippet}
</DetailView>
