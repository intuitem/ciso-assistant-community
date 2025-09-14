<script lang="ts">
	import type { ActionData, PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import LossExceedanceCurve from '$lib/components/Chart/LossExceedanceCurve.svelte';
	import LognormalDistribution from '$lib/components/Chart/LognormalDistribution.svelte';
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
	let simulationIsLoading = $state(false);
	let showDistributionModal = $state(false);
	let calculatedMu = $state<number | undefined>();
	let calculatedSigma = $state<number | undefined>();
	let xAxisScale = $state<'linear' | 'log'>('linear');

	const toastStore = getToastStore();

	run(() => {
		if (form?.message?.simulationComplete) {
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
			<form
				method="POST"
				action="?/runSimulation"
				use:enhance={() => {
					simulationIsLoading = true;
					return async ({ result, update }) => {
						await update();
						simulationIsLoading = false;

						// Handle responses immediately in the enhance callback
						if (result.type === 'success') {
							if (result.data?.error) {
								const errorData = result.data.message;
								toastStore.trigger({
									message: `Simulation Failed: ${errorData.details || errorData.error || 'Unknown error occurred'}`,
									background: 'bg-red-400 text-white',
									timeout: 2000,
									autohide: true
								});
							} else if (result.data?.success) {
								toastStore.trigger({
									message: 'Simulation completed successfully!',
									background: 'bg-green-500 text-white',
									autohide: true,
									timeout: 2000
								});
							}
						}
					};
				}}
			>
				<button
					type="submit"
					class="btn bg-pink-500 text-white h-fit"
					disabled={simulationIsLoading}
				>
					<span class="mr-2">
						{#if simulationIsLoading}
							<ProgressRing
								strokeWidth="16px"
								meterStroke="stroke-white"
								size="size-6"
								classes="-ml-2"
							/>
						{:else}
							<i class="fa-solid fa-play"></i>
						{/if}
					</span>
					Run simulation
				</button>
			</form>
		</div>
	{/snippet}

	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4 bg-slate-100 rounded-xl p-4">
			{#if data.lec?.data && Array.isArray(data.lec.data) && data.lec.data.length > 0}
				<!-- LEC Chart -->
				<div class="bg-white rounded-lg p-4 shadow-sm w-full">
					{#key data.lec.simulation_timestamp}
						<LossExceedanceCurve
							data={data.lec.data}
							toleranceData={data.data.risk_tolerance_curve}
							lossThreshold={data.data.loss_threshold}
							currency={data.data.currency || '$'}
							height="h-96"
							width="w-full"
							classesContainer="min-w-0"
							enableTooltip={true}
							autoYMax={true}
							autoXMax={true}
						/>
					{/key}
				</div>
			{:else}
				<!-- Show message for stale or missing data -->
				<div class="bg-white rounded-lg p-8 text-center shadow-sm">
					{#if data.lec?.message}
						<div class="text-orange-600 mb-4">
							<i class="fa-solid fa-triangle-exclamation text-2xl mb-2"></i>
							<p class="font-medium">{data.lec.message}</p>
						</div>
					{:else}
						<div class="text-gray-500">
							<i class="fa-solid fa-chart-line text-2xl mb-2"></i>
							<p>No LEC data available. Run a simulation to generate the chart.</p>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Risk Metrics -->
			<div class="bg-white rounded-lg p-6 shadow-sm">
				<div class="flex justify-between items-center mb-4">
					<h3 class="text-lg font-semibold">Risk Insights</h3>
					{#if data.data.impact?.lb && data.data.impact?.ub}
						<button
							onclick={() => (showDistributionModal = true)}
							class="text-sm text-blue-600 hover:text-blue-800 underline"
						>
							View Distribution
						</button>
					{/if}
				</div>
				{#if data.lec?.metrics && Object.keys(data.lec.metrics).length > 0}
					{@const metrics = data.lec.metrics}
					{@const currency = data.data.currency || '$'}
					{@const formatCurrency = (value) => {
						if (value >= 1000000000) return `${currency}${(value / 1000000000).toFixed(1)}B`;
						if (value >= 1000000) return `${currency}${(value / 1000000).toFixed(1)}M`;
						if (value >= 1000) return `${currency}${(value / 1000).toFixed(0)}K`;
						return `${currency}${Math.round(value).toLocaleString()}`;
					}}
					{@const scenarioLosses = Object.entries(metrics)
						.filter(([key, _]) => key.startsWith('loss_with_') && key.endsWith('_percent'))
						.map(([key, value]) => {
							const percentage = parseFloat(
								key.replace('loss_with_', '').replace('_percent', '').replace('_', '.')
							);
							return { key, value, percentage };
						})
						.sort((a, b) => b.percentage - a.percentage)}

					<!-- Risk Metrics - First Row: VaR Metrics -->
					<div class="mb-8">
						<h4 class="text-md font-medium text-gray-700 mb-4">Value at Risk Metrics</h4>
						<div class="grid grid-cols-2 md:grid-cols-4 gap-6">
							{#if metrics.mean_annual_loss !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-blue-600 mb-2">
										{formatCurrency(metrics.mean_annual_loss)}
									</div>
									<div class="text-sm text-gray-600">Mean Annual Loss</div>
								</div>
							{/if}
							{#if metrics.var_95 !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-orange-600 mb-2">
										{formatCurrency(metrics.var_95)}
									</div>
									<div class="text-sm text-gray-600">VaR 95%</div>
								</div>
							{/if}
							{#if metrics.var_99 !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-red-600 mb-2">
										{formatCurrency(metrics.var_99)}
									</div>
									<div class="text-sm text-gray-600">VaR 99%</div>
								</div>
							{/if}
							{#if metrics.var_999 !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-red-800 mb-2">
										{formatCurrency(metrics.var_999)}
									</div>
									<div class="text-sm text-gray-600">VaR 99.9%</div>
								</div>
							{/if}
						</div>
					</div>

					<!-- Loss Probabilities - Second Row -->
					<div class="mb-8">
						<h4 class="text-md font-medium text-gray-700 mb-4">Loss Probabilities</h4>
						<div class="grid grid-cols-2 md:grid-cols-5 gap-6">
							{#if metrics.prob_zero_loss !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-green-600 mb-2">
										{(metrics.prob_zero_loss * 100).toFixed(1)}%
									</div>
									<div class="text-sm text-gray-600">Zero Loss</div>
								</div>
							{/if}
							{#if metrics.prob_above_threshold !== undefined && data.data.loss_threshold}
								<div
									class="text-center p-3 bg-purple-50 border-2 border-purple-200 rounded-lg shadow-sm"
								>
									<div class="text-2xl font-bold text-purple-600 mb-2">
										{(metrics.prob_above_threshold * 100).toFixed(2)}%
									</div>
									<div class="text-sm text-gray-600">
										Over {data.data.loss_threshold_display ||
											`${currency}${data.data.loss_threshold.toLocaleString()}`}
									</div>
								</div>
							{/if}
							{#if metrics.prob_above_10k !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-yellow-600 mb-2">
										{(metrics.prob_above_10k * 100).toFixed(2)}%
									</div>
									<div class="text-sm text-gray-600">Over {currency}10K</div>
								</div>
							{/if}
							{#if metrics.prob_above_100k !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-orange-600 mb-2">
										{(metrics.prob_above_100k * 100).toFixed(2)}%
									</div>
									<div class="text-sm text-gray-600">Over {currency}100K</div>
								</div>
							{/if}
							{#if metrics.prob_above_1M !== undefined}
								<div class="text-center">
									<div class="text-2xl font-bold text-red-600 mb-2">
										{(metrics.prob_above_1M * 100).toFixed(2)}%
									</div>
									<div class="text-sm text-gray-600">Over {currency}1M</div>
								</div>
							{/if}
						</div>
					</div>

					<!-- Probability-Based Losses - Third Row -->
					<div>
						<h4 class="text-md font-medium text-gray-700 mb-4">Scenario-Based Losses</h4>
						<div class="grid grid-cols-2 md:grid-cols-4 gap-6">
							{#each scenarioLosses as { key, value, percentage }}
								<div class="text-center">
									<div class="text-2xl font-bold text-purple-600 mb-2">
										{formatCurrency(value)}
									</div>
									<div class="text-sm text-gray-600">Loss with {percentage}% chance</div>
								</div>
							{/each}
						</div>
					</div>
				{:else}
					<div class="text-center text-gray-500">
						{#if data.lec?.message}
							<i class="fa-solid fa-calculator text-2xl mb-2"></i>
							<p>No metrics available. {data.lec.message}</p>
						{:else}
							<i class="fa-solid fa-calculator text-2xl mb-2"></i>
							<p>No metrics available. Run a simulation to see risk insights.</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/snippet}
</DetailView>

<!-- Distribution Modal -->
{#if showDistributionModal}
	<div
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
		onclick={(e) => {
			if (e.target === e.currentTarget) showDistributionModal = false;
		}}
	>
		<div class="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-auto">
			<div class="flex justify-between items-center mb-4">
				<h2 class="text-xl font-semibold">Impact Distribution</h2>
				<div class="flex items-center space-x-4">
					<div class="flex items-center space-x-2">
						<label class="text-sm font-medium">X-axis:</label>
						<button
							onclick={() => (xAxisScale = xAxisScale === 'linear' ? 'log' : 'linear')}
							class="px-3 py-1 text-sm rounded border {xAxisScale === 'linear'
								? 'bg-blue-100 border-blue-300 text-blue-700'
								: 'bg-gray-100 border-gray-300'}"
						>
							Linear
						</button>
						<button
							onclick={() => (xAxisScale = xAxisScale === 'log' ? 'linear' : 'log')}
							class="px-3 py-1 text-sm rounded border {xAxisScale === 'log'
								? 'bg-blue-100 border-blue-300 text-blue-700'
								: 'bg-gray-100 border-gray-300'}"
						>
							Log
						</button>
					</div>
					<button
						onclick={() => (showDistributionModal = false)}
						class="text-gray-500 hover:text-gray-700 text-2xl"
					>
						×
					</button>
				</div>
			</div>
			<div class="mb-4">
				{#key xAxisScale}
					<LognormalDistribution
						lowerBound={data.data.impact?.lb}
						upperBound={data.data.impact?.ub}
						height="h-96"
						width="w-full"
						{xAxisScale}
						onParametersCalculated={(mu, sigma) => {
							calculatedMu = mu;
							calculatedSigma = sigma;
						}}
					/>
				{/key}
			</div>
			<div class="text-sm text-gray-600 space-y-2">
				<p class="text-center">
					Lognormal distribution with 90% confidence interval: ${data.data.impact?.lb?.toLocaleString()}
					- ${data.data.impact?.ub?.toLocaleString()}
				</p>
				{#if calculatedMu !== undefined && calculatedSigma !== undefined}
					<p class="text-center font-mono">
						Estimated parameters: μ = {calculatedMu.toFixed(4)}, σ = {calculatedSigma.toFixed(4)}
					</p>
				{/if}
			</div>
		</div>
	</div>
{/if}
