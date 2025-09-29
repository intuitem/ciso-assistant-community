<script lang="ts">
	import type { PageData } from './$types';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';
	import { goto } from '$app/navigation';
	import { Grid, Willow } from 'wx-svelte-grid';
	import ALETimelineRaceChart from '$lib/components/Chart/ALETimelineRaceChart.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Column visibility state management
	let columnVisibility = $state({
		scenario: true,
		level: true,
		ale: true,
		var_95: true,
		var_99: true,
		var_999: true,
		probability: true
	});
	let showColumnControls = $state(false);

	// Enhanced function to format currency values with better rounding and units
	function formatCurrency(value: number | null, currency: string): string {
		if (value === null || value === undefined) return 'N/A';

		const absValue = Math.abs(value);

		if (absValue >= 1000000000) {
			// Billions: 1-2 decimal places
			const billions = value / 1000000000;
			return `${currency}${billions.toFixed(billions >= 10 ? 1 : 2)}B`;
		} else if (absValue >= 1000000) {
			// Millions: 1-2 decimal places
			const millions = value / 1000000;
			return `${currency}${millions.toFixed(millions >= 10 ? 1 : 2)}M`;
		} else if (absValue >= 10000) {
			// Tens of thousands: round to nearest K
			const thousands = value / 1000;
			return `${currency}${Math.round(thousands)}K`;
		} else if (absValue >= 1000) {
			// Thousands: 1 decimal place for precision
			const thousands = value / 1000;
			return `${currency}${thousands.toFixed(1)}K`;
		} else if (absValue >= 100) {
			// Hundreds: no decimals
			return `${currency}${Math.round(value)}`;
		} else {
			// Under 100: 1-2 decimal places
			return `${currency}${value.toFixed(value >= 10 ? 1 : 2)}`;
		}
	}

	// Enhanced function to format probability as percentage with appropriate precision
	function formatProbability(value: number | null): string {
		if (value === null || value === undefined) return 'N/A';

		const percentage = value * 100;

		if (percentage >= 10) {
			// 10% and above: 1 decimal place
			return `${percentage.toFixed(1)}%`;
		} else if (percentage >= 1) {
			// 1-10%: 2 decimal places
			return `${percentage.toFixed(2)}%`;
		} else if (percentage >= 0.1) {
			// 0.1-1%: 3 decimal places
			return `${percentage.toFixed(3)}%`;
		} else if (percentage > 0) {
			// Very small percentages: 4 decimal places or scientific notation
			return percentage < 0.001 ? `${percentage.toExponential(2)}%` : `${percentage.toFixed(4)}%`;
		} else {
			// Zero
			return '0%';
		}
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
					var_95: scenario.current_level.var_95,
					var_99: scenario.current_level.var_99,
					var_999: scenario.current_level.var_999,
					probability: scenario.current_level.proba_of_exceeding_threshold,
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
					var_95: scenario.residual_level.var_95,
					var_99: scenario.residual_level.var_99,
					var_999: scenario.residual_level.var_999,
					probability: scenario.residual_level.proba_of_exceeding_threshold,
					scenario_id: scenario.id,
					level_type: 'residual'
				});
			}
		});

		return gridData;
	}

	// Prepare data for ALE timeline race chart
	function prepareTimelineChartData(keyMetricsData: any) {
		if (!keyMetricsData?.scenarios) return [];

		return keyMetricsData.scenarios
			.filter((scenario: any) => {
				// Include scenarios that have at least current ALE data
				const hasCurrentALE =
					scenario.current_level &&
					scenario.current_level.ale !== null &&
					scenario.current_level.ale !== undefined;
				const hasResidualALE =
					scenario.residual_level &&
					scenario.residual_level.ale !== null &&
					scenario.residual_level.ale !== undefined;

				// At minimum, we need current ALE. If no residual ALE, we'll use current ALE as fallback
				return hasCurrentALE;
			})
			.map((scenario: any) => ({
				id: scenario.id,
				name: scenario.name,
				currentALE: scenario.current_level?.ale || 0,
				residualALE: scenario.residual_level?.ale || scenario.current_level?.ale || 0,
				treatmentControls: scenario.treatment_controls || []
			}));
	}

	// Helper functions for column formatting
	const formatCurrencyForGrid = (value: any, currency: string = '€') => {
		if (value === null || value === undefined) return 'N/A';
		return formatCurrency(value, currency);
	};

	const formatProbabilityForGrid = (value: any) => {
		if (value === null || value === undefined) return 'N/A';
		return formatProbability(value);
	};

	// Define all available grid columns with sorting and built-in filtering
	const getAllColumns = (currency: string = '€') => [
		{
			id: 'scenario',
			header: {
				text: m.scenario(),
				filter: {
					type: 'text',
					config: {
						placeholder: m.filterByScenarioName()
					}
				}
			},
			flexgrow: 2,
			sort: true,
			displayName: m.scenario()
		},
		{
			id: 'level',
			header: {
				text: m.level(),
				filter: {
					type: 'richselect',
					config: {
						placeholder: 'Filter by level...',
						options: [
							{ id: '', label: m.allLevels() },
							{ id: 'Current', label: m.current() },
							{ id: 'Residual', label: m.residual() }
						]
					}
				}
			},
			flexgrow: 1,
			sort: true,
			displayName: m.level()
		},
		{
			id: 'ale',
			header: { text: m.ale() },
			flexgrow: 1,
			sort: true,
			template: (value: any, row: any, col: any) => formatCurrency(value, currency),
			displayName: m.ale()
		},
		{
			id: 'var_95',
			header: { text: m.var95() },
			flexgrow: 1,
			sort: true,
			template: (value: any, row: any, col: any) => formatCurrency(value, currency),
			displayName: m.var95()
		},
		{
			id: 'var_99',
			header: { text: m.var99() },
			flexgrow: 1,
			sort: true,
			template: (value: any, row: any, col: any) => formatCurrency(value, currency),
			displayName: m.var99()
		},
		{
			id: 'var_999',
			header: { text: m.var999() },
			flexgrow: 1,
			sort: true,
			template: (value: any, row: any, col: any) => formatCurrency(value, currency),
			displayName: m.var999()
		},
		{
			id: 'probability',
			header: { text: m.pThreshold() },
			flexgrow: 1,
			sort: true,
			template: (value: any, row: any, col: any) => formatProbability(value),
			displayName: m.pThreshold()
		}
	];

	// Create reactive columns and get all columns list
	const allColumns = $derived.by(() => getAllColumns('€')); // We'll update currency later when we have the data

	// Filter columns based on visibility settings
	const visibleColumns = $derived(
		allColumns.filter((column) => columnVisibility[column.id as keyof typeof columnVisibility])
	);

	// Functions for column management
	function toggleAllColumns(show: boolean) {
		if (!show && getVisibleColumnsCount() <= 1) {
			// Prevent hiding all columns - keep at least one visible
			return;
		}

		Object.keys(columnVisibility).forEach((key) => {
			columnVisibility[key as keyof typeof columnVisibility] = show;
		});
	}

	function toggleColumn(columnId: string, checked: boolean) {
		if (!checked && getVisibleColumnsCount() <= 1) {
			// Prevent hiding the last visible column
			return;
		}
		columnVisibility[columnId as keyof typeof columnVisibility] = checked;
	}

	function getVisibleColumnsCount() {
		return Object.values(columnVisibility).filter(Boolean).length;
	}

	// Close column controls when clicking outside
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as Element;
		const dropdown = target.closest('.column-controls-dropdown');
		const button = target.closest('.column-controls-button');

		if (!dropdown && !button && showColumnControls) {
			showColumnControls = false;
		}
	}
</script>

<svelte:head>
	<title>{m.keyMetrics()} - {m.quantitativeRiskStudyLabel()}</title>
</svelte:head>

<div class="container mx-auto px-4 py-8" on:click={handleClickOutside}>
	<!-- Header -->
	<div class="flex items-center justify-between mb-8">
		<div>
			<h1 class="text-3xl font-bold text-gray-900">{m.keyMetrics()}</h1>
			<p class="text-gray-600 mt-2">{m.advancedAnalysisMetrics()}</p>
		</div>
		<button
			class="btn variant-ghost-surface"
			on:click={() => goto(`/quantitative-risk-studies/${$page.params.id}`)}
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>
			{m.backToStudy()}
		</button>
	</div>

	{#await data.stream.keyMetrics}
		<!-- Loading State -->
		<div class="flex justify-center items-center h-64">
			<div class="flex flex-col items-center space-y-4">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
				<p class="text-gray-600">{m.loadingKeyMetrics()}</p>
			</div>
		</div>
	{:then keyMetricsData}
		{#if keyMetricsData && keyMetricsData.scenarios}
			<!-- Study Overview -->
			<div class="bg-white rounded-lg p-6 shadow-sm mb-8">
				<div class="flex justify-between items-center mb-4">
					<h2 class="text-xl font-semibold text-gray-900">{m.studyOverview()}</h2>
					<div class="text-sm text-gray-600">
						{keyMetricsData.currency} • {keyMetricsData.total_scenarios}
						{m.scenarios()}
					</div>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					<div class="bg-blue-50 rounded-lg p-4 text-center">
						<div class="text-2xl font-bold text-blue-600">
							{keyMetricsData.scenarios_with_current_data}
						</div>
						<div class="text-sm text-gray-600">{m.scenariosWithCurrentData()}</div>
					</div>
					<div class="bg-green-50 rounded-lg p-4 text-center">
						<div class="text-2xl font-bold text-green-600">
							{keyMetricsData.scenarios_with_residual_data}
						</div>
						<div class="text-sm text-gray-600">{m.scenariosWithResidualData()}</div>
					</div>
					<div class="bg-purple-50 rounded-lg p-4 text-center">
						<div class="text-2xl font-bold text-purple-600">
							{keyMetricsData.loss_threshold_display}
						</div>
						<div class="text-sm text-gray-600">{m.lossThresholdLabel()}</div>
					</div>
				</div>
			</div>

			<!-- ALE Timeline Race Chart -->
			{@const timelineChartData = prepareTimelineChartData(keyMetricsData)}
			{#if timelineChartData.length > 0}
				<div class="mb-8">
					<ALETimelineRaceChart
						scenarios={timelineChartData}
						currency={keyMetricsData.currency}
						title={m.aleEvolutionTimeline()}
						height="h-auto"
						autoPlay={false}
						animationSpeed={1500}
					/>
				</div>
			{:else}
				<!-- Debug information when chart doesn't show -->
				<div class="mb-8 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
					<h3 class="text-lg font-semibold text-yellow-800 mb-2">
						<i class="fa-solid fa-info-circle mr-2"></i>
						ALE Timeline Chart Debug Info
					</h3>
					<div class="text-sm text-yellow-700 space-y-1">
						<p><strong>Total {m.scenarios()}:</strong> {keyMetricsData?.scenarios?.length || 0}</p>
						<p>
							<strong>{m.scenariosWithCurrentLevel()}</strong>
							{keyMetricsData?.scenarios?.filter((s) => s.current_level)?.length || 0}
						</p>
						<p>
							<strong>{m.scenariosWithResidualLevel()}</strong>
							{keyMetricsData?.scenarios?.filter((s) => s.residual_level)?.length || 0}
						</p>
						<p>
							<strong>{m.scenariosWithBothLevels()}</strong>
							{keyMetricsData?.scenarios?.filter((s) => s.current_level && s.residual_level)
								?.length || 0}
						</p>
						<p>
							<strong>{m.scenariosWithTreatmentControls()}</strong>
							{keyMetricsData?.scenarios?.filter(
								(s) => s.treatment_controls && s.treatment_controls.length > 0
							)?.length || 0}
						</p>
						<details class="mt-2">
							<summary class="cursor-pointer font-medium">View raw scenario data</summary>
							<pre class="mt-2 p-2 bg-yellow-100 rounded text-xs overflow-auto">{JSON.stringify(
									keyMetricsData?.scenarios,
									null,
									2
								)}</pre>
						</details>
					</div>
				</div>
			{/if}

			<!-- Scenarios Grid -->
			<div class="bg-white rounded-lg shadow-sm overflow-hidden">
				<div class="px-6 py-4 border-b border-gray-200">
					<div class="flex justify-between items-start">
						<div>
							<h2 class="text-xl font-semibold text-gray-900">{m.riskScenariosAnalysis()}</h2>
							<p class="text-sm text-gray-600 mt-1">
								{m.detailedMetricsForEachRisk()}
							</p>
						</div>
						<div class="flex items-center space-x-2">
							<span class="text-sm text-gray-500">
								{getVisibleColumnsCount()}
								{m.columnsOfColumns()}
								{allColumns.length}
								{m.columns()}
							</span>
							<div class="relative">
								<button
									class="btn btn-sm variant-ghost-surface column-controls-button"
									on:click={() => (showColumnControls = !showColumnControls)}
									title="Show/Hide Columns"
								>
									<i class="fa-solid fa-columns text-sm mr-1"></i>
									{m.columns()}
								</button>

								{#if showColumnControls}
									<div
										class="absolute right-0 top-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-10 min-w-[250px] column-controls-dropdown"
									>
										<div class="flex justify-between items-center mb-3">
											<h4 class="font-medium text-gray-900">{m.showHideColumns()}</h4>
											<button
												class="text-gray-400 hover:text-gray-600"
												on:click={() => (showColumnControls = false)}
											>
												<i class="fa-solid fa-times"></i>
											</button>
										</div>

										<div class="flex gap-2 mb-3">
											<button
												class="btn btn-sm variant-ghost-primary"
												on:click={() => toggleAllColumns(true)}
												disabled={getVisibleColumnsCount() === allColumns.length}
											>
												{m.showAll()}
											</button>
											<button
												class="btn btn-sm variant-ghost-error"
												on:click={() => toggleAllColumns(false)}
												disabled={getVisibleColumnsCount() <= 1}
											>
												{m.hideAll()}
											</button>
										</div>

										<div class="space-y-2 max-h-64 overflow-y-auto">
											{#each allColumns as column}
												{@const isLastVisible =
													getVisibleColumnsCount() === 1 && columnVisibility[column.id]}
												<label
													class="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-1 rounded {isLastVisible
														? 'opacity-50'
														: ''}"
												>
													<input
														type="checkbox"
														checked={columnVisibility[column.id]}
														on:change={(e) => toggleColumn(column.id, e.target?.checked || false)}
														disabled={isLastVisible}
														class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded disabled:opacity-50"
													/>
													<span class="text-sm text-gray-700">{column.displayName}</span>
													{#if isLastVisible}
														<span class="text-xs text-gray-400">({m.required()})</span>
													{/if}
												</label>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>

				<div class="p-4">
					<div style="height: 500px; width: 100%;">
						<Willow>
							<Grid
								data={prepareGridData(keyMetricsData)}
								columns={visibleColumns}
								headerHeight={40}
								rowHeight={45}
							/>
						</Willow>
					</div>
				</div>
			</div>

			<!-- Legend and Notes -->
			<div class="mt-8 bg-gray-50 rounded-lg p-6">
				<h3 class="text-lg font-semibold text-gray-900 mb-4">{m.legendNotes()}</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div>
						<h4 class="font-medium text-gray-900 mb-2">{m.metricsDefinitions()}</h4>
						<ul class="text-sm text-gray-600 space-y-1">
							<li><strong>{m.ale()}:</strong> {m.annualLossExpectancy()}</li>
							<li><strong>VaR:</strong> {m.valueAtRisk()}</li>
							<li><strong>P(>Threshold):</strong> {m.probabilityExceedingThreshold()}</li>
						</ul>
					</div>
					<div>
						<h4 class="font-medium text-gray-900 mb-2">{m.riskLevels()}</h4>
						<ul class="text-sm text-gray-600 space-y-1">
							<li><strong>{m.current()}:</strong> {m.currentRiskWithExistingControls()}</li>
							<li><strong>{m.residual()}:</strong> {m.residualRiskAfterTreatment()}</li>
						</ul>
					</div>
				</div>
			</div>
		{:else}
			<!-- Empty State -->
			<div class="bg-white rounded-lg p-8 shadow-sm text-center">
				<div class="flex flex-col items-center space-y-4">
					<i class="fa-solid fa-chart-simple text-4xl text-gray-400"></i>
					<h3 class="text-lg font-semibold text-gray-600">{m.noKeyMetricsAvailable()}</h3>
					<p class="text-gray-500 max-w-md">
						{m.noSimulationDataFound()}
					</p>
				</div>
			</div>
		{/if}
	{:catch error}
		<!-- Error State -->
		<div class="bg-white rounded-lg p-8 shadow-sm text-center">
			<div class="flex flex-col items-center space-y-4">
				<i class="fa-solid fa-triangle-exclamation text-4xl text-red-400"></i>
				<h3 class="text-lg font-semibold text-gray-600">{m.failedToLoadKeyMetrics()}</h3>
				<p class="text-gray-500 max-w-md">
					{m.thereWasAnErrorLoading()}
				</p>
			</div>
		</div>
	{/await}
</div>
