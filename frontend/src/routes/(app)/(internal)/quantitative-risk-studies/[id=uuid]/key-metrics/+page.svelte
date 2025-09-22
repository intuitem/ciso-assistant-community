<script lang="ts">
	import type { PageData } from './$types';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Grid, Willow } from 'wx-svelte-grid';

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

	// Prepare grid data from scenarios (flat structure)
	function prepareGridData(keyMetricsData: any) {
		if (!keyMetricsData?.scenarios) return [];

		const gridData: any[] = [];

		keyMetricsData.scenarios.forEach((scenario: any, index: number) => {
			// Add current level row if exists
			if (scenario.current_level) {
				gridData.push({
					id: `${scenario.id}-current`,
					scenario: scenario.name,
					level: 'Current',
					ale: scenario.current_level.ale,
					ale_formatted: formatCurrency(scenario.current_level.ale, keyMetricsData.currency),
					var_95: scenario.current_level.var_95,
					var_95_formatted: formatCurrency(scenario.current_level.var_95, keyMetricsData.currency),
					var_99: scenario.current_level.var_99,
					var_99_formatted: formatCurrency(scenario.current_level.var_99, keyMetricsData.currency),
					var_999: scenario.current_level.var_999,
					var_999_formatted: formatCurrency(scenario.current_level.var_999, keyMetricsData.currency),
					probability: scenario.current_level.proba_of_exceeding_threshold,
					probability_formatted: formatProbability(scenario.current_level.proba_of_exceeding_threshold),
					scenario_id: scenario.id,
					level_type: 'current'
				});
			}

			// Add residual level row if exists
			if (scenario.residual_level) {
				gridData.push({
					id: `${scenario.id}-residual`,
					scenario: scenario.name,
					level: 'Residual',
					ale: scenario.residual_level.ale,
					ale_formatted: formatCurrency(scenario.residual_level.ale, keyMetricsData.currency),
					var_95: scenario.residual_level.var_95,
					var_95_formatted: formatCurrency(scenario.residual_level.var_95, keyMetricsData.currency),
					var_99: scenario.residual_level.var_99,
					var_99_formatted: formatCurrency(scenario.residual_level.var_99, keyMetricsData.currency),
					var_999: scenario.residual_level.var_999,
					var_999_formatted: formatCurrency(scenario.residual_level.var_999, keyMetricsData.currency),
					probability: scenario.residual_level.proba_of_exceeding_threshold,
					probability_formatted: formatProbability(scenario.residual_level.proba_of_exceeding_threshold),
					scenario_id: scenario.id,
					level_type: 'residual'
				});
			}
		});

		return gridData;
	}


	// Define grid columns with sorting and built-in filtering
	const columns = [
		{
			id: 'scenario',
			header: {
				text: 'Scenario',
				filter: {
					type: 'text',
					config: {
						placeholder: 'Filter by scenario name...'
					}
				}
			},
			flexgrow: 2,
			sort: true
		},
		{
			id: 'level',
			header: {
				text: 'Level',
				filter: {
					type: 'richselect',
					config: {
						placeholder: 'Filter by level...',
						options: [
							{ id: '', label: 'All Levels' },
							{ id: 'Current', label: 'Current' },
							{ id: 'Residual', label: 'Residual' }
						]
					}
				}
			},
			flexgrow: 1,
			sort: true
		},
		{
			id: 'ale_formatted',
			header: { text: 'ALE' },
			flexgrow: 1,
			sort: true
		},
		{
			id: 'var_95_formatted',
			header: { text: 'VaR 95%' },
			flexgrow: 1,
			sort: true
		},
		{
			id: 'var_99_formatted',
			header: { text: 'VaR 99%' },
			flexgrow: 1,
			sort: true
		},
		{
			id: 'var_999_formatted',
			header: { text: 'VaR 99.9%' },
			flexgrow: 1,
			sort: true
		},
		{
			id: 'probability_formatted',
			header: { text: 'P(>Threshold)' },
			flexgrow: 1,
			sort: true
		}
	];
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
			on:click={() => goto(`/quantitative-risk-studies/${$page.params.id}`)}
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

			<!-- Scenarios Grid -->
			<div class="bg-white rounded-lg shadow-sm overflow-hidden">
				<div class="px-6 py-4 border-b border-gray-200">
					<h2 class="text-xl font-semibold text-gray-900">Risk Scenarios Analysis</h2>
					<p class="text-sm text-gray-600 mt-1">Detailed metrics for each risk scenario - click column headers to sort, use filter controls in Scenario and Level columns</p>
				</div>


				<div class="p-4">
					<div style="height: 500px; width: 100%;">
						<Willow>
							<Grid
								data={prepareGridData(keyMetricsData)}
								{columns}
								headerHeight={40}
								rowHeight={45}
							/>
						</Willow>
					</div>
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
