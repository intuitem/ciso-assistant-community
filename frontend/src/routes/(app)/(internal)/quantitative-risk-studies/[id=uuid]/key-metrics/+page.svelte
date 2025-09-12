<script lang="ts">
	import type { PageData } from './$types';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Function to format currency values
	function formatCurrency(value: number | null, currency: string): string {
		if (value === null || value === undefined) return 'N/A';
		if (value >= 1000000000) {
			return `${currency}${(value / 1000000000).toFixed(1)}B`;
		} else if (value >= 1000000) {
			return `${currency}${(value / 1000000).toFixed(1)}M`;
		} else if (value >= 1000) {
			return `${currency}${(value / 1000).toFixed(0)}K`;
		} else {
			return `${currency}${value.toLocaleString()}`;
		}
	}

	// Function to format probability as percentage
	function formatProbability(value: number | null): string {
		if (value === null || value === undefined) return 'N/A';
		return `${(value * 100).toFixed(2)}%`;
	}
</script>

<svelte:head>
	<title>Key Metrics - Quantitative Risk Study</title>
</svelte:head>

<div class="container mx-auto px-4 py-8">
	<!-- Header -->
	<div class="flex items-center justify-between mb-8">
		<div>
			<h1 class="text-3xl font-bold text-gray-900">Key Metrics</h1>
			<p class="text-gray-600 mt-2">Advanced analysis metrics for quantitative risk scenarios</p>
		</div>
		<button
			class="btn variant-ghost-surface"
			on:click={() => goto(`/quantitative-risk-studies/${page.params.id}`)}
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>
			Back to Study
		</button>
	</div>

	{#await data.stream.keyMetrics}
		<!-- Loading State -->
		<div class="flex justify-center items-center h-64">
			<div class="flex flex-col items-center space-y-4">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
				<p class="text-gray-600">Loading key metrics...</p>
			</div>
		</div>
	{:then keyMetricsData}
		{#if keyMetricsData && keyMetricsData.scenarios}
			<!-- Study Overview -->
			<div class="bg-white rounded-lg p-6 shadow-sm mb-8">
				<div class="flex justify-between items-center mb-4">
					<h2 class="text-xl font-semibold text-gray-900">Study Overview</h2>
					<div class="text-sm text-gray-600">
						{keyMetricsData.currency} • {keyMetricsData.total_scenarios} scenarios
					</div>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<div class="bg-blue-50 rounded-lg p-4 text-center">
						<div class="text-2xl font-bold text-blue-600">
							{keyMetricsData.scenarios_with_current_data}
						</div>
						<div class="text-sm text-gray-600">Scenarios with Current Data</div>
					</div>
					<div class="bg-green-50 rounded-lg p-4 text-center">
						<div class="text-2xl font-bold text-green-600">
							{keyMetricsData.scenarios_with_residual_data}
						</div>
						<div class="text-sm text-gray-600">Scenarios with Residual Data</div>
					</div>
					<div class="bg-purple-50 rounded-lg p-4 text-center">
						<div class="text-2xl font-bold text-purple-600">
							{keyMetricsData.loss_threshold_display}
						</div>
						<div class="text-sm text-gray-600">Loss Threshold</div>
					</div>
				</div>
			</div>

			<!-- Scenarios Table -->
			<div class="bg-white rounded-lg shadow-sm overflow-hidden">
				<div class="px-6 py-4 border-b border-gray-200">
					<h2 class="text-xl font-semibold text-gray-900">Risk Scenarios Analysis</h2>
					<p class="text-sm text-gray-600 mt-1">Detailed metrics for each risk scenario</p>
				</div>

				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200">
						<thead class="bg-gray-50">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
								>
									Scenario
								</th>
								<th
									class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
								>
									Level
								</th>
								<th
									class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
								>
									ALE
								</th>
								<th
									class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
								>
									VaR 95%
								</th>
								<th
									class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
								>
									VaR 99%
								</th>
								<th
									class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
								>
									VaR 99.9%
								</th>
								<th
									class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider"
								>
									P(>Threshold)
								</th>
							</tr>
						</thead>
						<tbody class="bg-white divide-y divide-gray-200">
							{#each keyMetricsData.scenarios as scenario}
								<!-- Current Level Row -->
								{#if scenario.current_level}
									<tr class="hover:bg-gray-50">
										<td class="px-6 py-4 whitespace-nowrap">
											<div class="text-sm font-medium text-gray-900">{scenario.name}</div>
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center">
											<span
												class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
											>
												Current
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.current_level.ale, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.current_level.var_95, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.current_level.var_99, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.current_level.var_999, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatProbability(scenario.current_level.proba_of_exceeding_threshold)}
										</td>
									</tr>
								{/if}

								<!-- Residual Level Row -->
								{#if scenario.residual_level}
									<tr class="hover:bg-gray-50">
										<td class="px-6 py-4 whitespace-nowrap">
											{#if !scenario.current_level}
												<div class="text-sm font-medium text-gray-900">{scenario.name}</div>
											{/if}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center">
											<span
												class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
											>
												Residual
											</span>
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.residual_level.ale, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.residual_level.var_95, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.residual_level.var_99, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatCurrency(scenario.residual_level.var_999, keyMetricsData.currency)}
										</td>
										<td class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
											{formatProbability(scenario.residual_level.proba_of_exceeding_threshold)}
										</td>
									</tr>
								{/if}

								<!-- Divider between scenarios -->
								{#if scenario !== keyMetricsData.scenarios[keyMetricsData.scenarios.length - 1]}
									<tr>
										<td colspan="7" class="px-6 py-1">
											<div class="border-b border-gray-100"></div>
										</td>
									</tr>
								{/if}
							{/each}
						</tbody>
					</table>
				</div>
			</div>

			<!-- Legend and Notes -->
			<div class="mt-8 bg-gray-50 rounded-lg p-6">
				<h3 class="text-lg font-semibold text-gray-900 mb-4">Legend & Notes</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div>
						<h4 class="font-medium text-gray-900 mb-2">Metrics Definitions</h4>
						<ul class="text-sm text-gray-600 space-y-1">
							<li><strong>ALE:</strong> Annual Loss Expectancy</li>
							<li><strong>VaR:</strong> Value at Risk at specified percentiles</li>
							<li><strong>P(>Threshold):</strong> Probability of exceeding loss threshold</li>
						</ul>
					</div>
					<div>
						<h4 class="font-medium text-gray-900 mb-2">Risk Levels</h4>
						<ul class="text-sm text-gray-600 space-y-1">
							<li><strong>Current:</strong> Risk with existing controls</li>
							<li><strong>Residual:</strong> Risk after implementing selected treatments</li>
						</ul>
					</div>
				</div>
			</div>
		{:else}
			<!-- Empty State -->
			<div class="bg-white rounded-lg p-8 shadow-sm text-center">
				<div class="flex flex-col items-center space-y-4">
					<i class="fa-solid fa-chart-simple text-4xl text-gray-400"></i>
					<h3 class="text-lg font-semibold text-gray-600">No Key Metrics Available</h3>
					<p class="text-gray-500 max-w-md">
						No simulation data found for this study. Please run simulations on your scenarios and
						hypotheses to generate key metrics.
					</p>
				</div>
			</div>
		{/if}
	{:catch error}
		<!-- Error State -->
		<div class="bg-white rounded-lg p-8 shadow-sm text-center">
			<div class="flex flex-col items-center space-y-4">
				<i class="fa-solid fa-triangle-exclamation text-4xl text-red-400"></i>
				<h3 class="text-lg font-semibold text-gray-600">Failed to Load Key Metrics</h3>
				<p class="text-gray-500 max-w-md">
					There was an error loading the key metrics data. Please try refreshing the page.
				</p>
			</div>
		</div>
	{/await}
</div>
