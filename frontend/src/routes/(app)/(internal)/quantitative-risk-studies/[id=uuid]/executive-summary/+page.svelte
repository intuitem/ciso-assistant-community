<script lang="ts">
	import type { PageData } from './$types';
	import { page } from '$app/state';
	import LossExceedanceCurve from '$lib/components/Chart/LossExceedanceCurve.svelte';
	import ALEComparisonChart from '$lib/components/Chart/ALEComparisonChart.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	let showAleBreakdownModal = $state(false);
</script>

<svelte:head>
	<title>{m.executiveSummary()} - CISO Assistant</title>
</svelte:head>

<main class="p-6 space-y-6">
	{#await Promise.all( [data.stream.executiveSummary, data.stream.combinedLec, data.stream.aleComparison] )}
		<!-- Breadcrumb loading state -->
		<div class="bg-white p-2 shadow rounded-lg space-x-2 flex flex-row justify-center mb-2">
			<p class="font-semibold text-lg">{m.loading()}</p>
		</div>
		<div class="flex items-center justify-center h-64">
			<div class="text-center">
				<LoadingSpinner />
				<p class="mt-4 text-gray-600">{m.loadingExecutiveSummary()}</p>
			</div>
		</div>
	{:then [summaryData, combinedLecData, aleComparisonData]}
		{#if summaryData}
			<!-- Breadcrumb -->

			<!-- Header -->
			<div class="bg-white rounded-lg p-6 shadow-sm">
				<div class="flex justify-between items-start mb-4">
					<div>
						<h1 class="text-2xl font-bold text-gray-900 mb-2">
							{summaryData.study_name}
						</h1>
						{#if summaryData.study_authors && summaryData.study_authors.length > 0}
							<div class="font-semibold text-gray-700 mb-2">
								{m.authors()}: {summaryData.study_authors.join(' | ')}
							</div>
						{/if}
						{#if summaryData.study_folder}
							<div class="font-semibold text-gray-700 mb-2">
								{m.domain()}: {summaryData.study_folder.name}
							</div>
						{/if}
						{#if summaryData.study_description}
							<div class="mb-4">
								<MarkdownRenderer content={summaryData.study_description} class="text-gray-600" />
							</div>
						{/if}
						{#if summaryData.study_assets && summaryData.study_assets.length > 0}
							<div class="mb-4">
								<div class="text-sm font-medium text-gray-700 mb-2">{m.assets()}:</div>
								<div class="flex flex-wrap gap-2">
									{#each summaryData.study_assets as asset}
										<Anchor
											href="/assets/{asset.id}"
											class="px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-800 text-sm font-medium rounded cursor-pointer transition-colors"
											breadcrumbAction="push"
										>
											{asset.name}
										</Anchor>
									{/each}
								</div>
							</div>
						{/if}
					</div>
					<Anchor
						href={`/quantitative-risk-studies/${page.params.id}`}
						class="btn preset-ghost-surface"
						breadcrumbAction="pop"
					>
						<i class="fa-solid fa-arrow-left mr-2"></i>{m.backToStudy()}
					</Anchor>
				</div>

				<!-- Risk Thresholds and Treatment Cost -->
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
					{#if summaryData.loss_threshold}
						<div class="text-center">
							<div class="text-sm text-gray-600 font-medium mb-1">{m.lossThresholdLabel()}</div>
							<div class="text-lg font-bold text-red-600">{summaryData.loss_threshold_display}</div>
							<div class="text-xs text-gray-500">{m.maximumAcceptableLoss()}</div>
						</div>
					{/if}
					{#if combinedLecData?.current_threshold_probability_display}
						<div class="text-center">
							<div class="text-sm text-gray-600 font-medium mb-1">{m.currentProfile()}</div>
							<div class="text-lg font-bold text-orange-600">
								{combinedLecData.current_threshold_probability_display}
							</div>
							<div class="text-xs text-gray-500">{m.probabilityToExceedThreshold()}</div>
						</div>
					{/if}
					{#if combinedLecData?.residual_threshold_probability_display}
						<div class="text-center">
							<div class="text-sm text-gray-600 font-medium mb-1">{m.residualProfile()}</div>
							<div class="text-lg font-bold text-green-600">
								{combinedLecData.residual_threshold_probability_display}
							</div>
							<div class="text-xs text-gray-500">{m.probabilityToExceedThreshold()}</div>
						</div>
					{/if}
					{#if summaryData.study_total_treatment_cost_display}
						<div class="text-center">
							<div class="text-sm text-gray-600 font-medium mb-1">{m.totalTreatmentCost()}</div>
							<div class="text-lg font-bold text-purple-600">
								{summaryData.study_total_treatment_cost_display}
							</div>
							<div class="text-xs text-gray-500">
								{summaryData.unique_added_controls_count || 0}
								{summaryData.unique_added_controls_count === 1
									? m.uniqueControl()
									: m.uniqueControls()}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Combined Loss Exceedance Curve -->
			{#if combinedLecData?.curves && combinedLecData.curves.length > 0}
				{@const curves = combinedLecData.curves}
				{@const currentRiskCurve = curves.find((c) => c.type === 'combined_current')}
				{@const residualRiskCurve = curves.find((c) => c.type === 'combined_residual')}
				{@const toleranceCurve = curves.find((c) => c.type === 'tolerance')}

				<div class="bg-white rounded-lg p-6 shadow-sm">
					<div class="flex justify-between items-center mb-4">
						<div class="flex items-center gap-3">
							<h2 class="text-xl font-semibold">{m.portfolioRiskProfile()}</h2>
							{#if aleComparisonData?.scenarios && aleComparisonData.scenarios.length > 0}
								<button
									onclick={() => (showAleBreakdownModal = true)}
									class="text-sm text-blue-600 hover:text-blue-800 underline flex items-center gap-1"
									title={m.viewAleBreakdownByScenario()}
								>
									<i class="fa-solid fa-chart-column"></i>
									{m.breakdown()}
								</button>
							{/if}
						</div>
						<div class="text-sm text-gray-600">
							{m.currentLabel()}: {combinedLecData.scenarios_with_current_data} / {combinedLecData.total_scenarios}
							{#if combinedLecData.scenarios_with_residual_data}
								| {m.residualLabel()}: {combinedLecData.scenarios_with_residual_data} / {combinedLecData.total_scenarios}
								{m.scenarios()}
							{/if}
						</div>
					</div>

					<div class="w-full">
						<LossExceedanceCurve
							name="combined-study-lec"
							data={currentRiskCurve?.data || []}
							residualData={residualRiskCurve?.data || []}
							toleranceData={toleranceCurve?.data || []}
							lossThreshold={summaryData.loss_threshold}
							currency={combinedLecData.currency}
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
				<!-- Empty State for Combined LEC Chart -->
				<div class="bg-white rounded-lg p-8 shadow-sm text-center">
					<div class="flex flex-col items-center space-y-4">
						<i class="fa-solid fa-chart-area text-4xl text-gray-400"></i>
						<h3 class="text-lg font-semibold text-gray-600">{m.portfolioOverview()}</h3>
						<p class="text-gray-500">
							{m.noCombinedLecDataAvailable()}
						</p>
					</div>
				</div>
			{/if}

			<!-- Scenarios -->
			{#if summaryData.scenarios && summaryData.scenarios.length > 0}
				<div class="space-y-6">
					{#each summaryData.scenarios as scenario (scenario.id)}
						<div class="card bg-white shadow-sm p-0">
							<div class="p-6 pb-4">
								<div class="flex justify-between items-start">
									<div class="flex-1">
										<div class="flex items-center justify-between mb-2">
											<div class="flex items-center gap-3">
												<Anchor
													href="/quantitative-risk-scenarios/{scenario.id}"
													class="px-2 py-1 bg-blue-100 hover:bg-blue-200 text-blue-800 text-sm font-medium rounded cursor-pointer transition-colors"
													breadcrumbAction="push"
												>
													{scenario.ref_id}
												</Anchor>
											</div>
											<div class="flex items-center gap-2">
												<span
													class="px-2 py-1 bg-green-100 text-green-800 text-sm font-medium rounded capitalize"
												>
													{safeTranslate(scenario.status)}
												</span>
												{#if scenario.priority}
													<span
														class="px-2 py-1 bg-gray-100 text-gray-800 text-sm font-medium rounded"
													>
														P{scenario.priority}
													</span>
												{/if}
											</div>
										</div>
										<h2 class="text-xl font-semibold text-gray-900 mb-2">{scenario.name}</h2>
										{#if scenario.description || scenario.observation}
											<div class="mb-4">
												<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
													{#if scenario.description}
														<div>
															<h4 class="text-sm font-medium text-gray-900 mb-2">
																{m.description()}
															</h4>
															<MarkdownRenderer
																content={scenario.description}
																class="text-gray-600"
															/>
														</div>
													{/if}
													{#if scenario.observation}
														<div>
															<h4 class="text-sm font-medium text-gray-900 mb-2">
																{m.observation()}
															</h4>
															<MarkdownRenderer
																content={scenario.observation}
																class="text-gray-600"
															/>
														</div>
													{/if}
												</div>
											</div>
										{/if}
									</div>
								</div>

								<!-- {m.assets()}, {m.threats()}, {m.qualifications()} -->
								<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
									{#if scenario.assets && scenario.assets.length > 0}
										<div>
											<h4 class="text-sm font-medium text-gray-900 mb-2">
												<i class="fa-solid fa-gem mr-1"></i>{m.assets()} ({scenario.assets.length})
											</h4>
											<div class="space-y-1">
												{#each scenario.assets.slice(0, 3) as asset}
													<div class="text-sm text-gray-600">• {asset.name}</div>
												{/each}
												{#if scenario.assets.length > 3}
													<div class="text-sm text-gray-500">
														{m.andMore()}
														{scenario.assets.length - 3}
														{m.more()}
													</div>
												{/if}
											</div>
										</div>
									{/if}

									{#if scenario.threats && scenario.threats.length > 0}
										<div>
											<h4 class="text-sm font-medium text-gray-900 mb-2">
												<i class="fa-solid fa-exclamation-triangle mr-1"></i>{m.threats()} ({scenario
													.threats.length})
											</h4>
											<div class="space-y-1">
												{#each scenario.threats.slice(0, 3) as threat}
													<div class="text-sm text-gray-600">• {threat.name}</div>
												{/each}
												{#if scenario.threats.length > 3}
													<div class="text-sm text-gray-500">
														{m.andMore()}
														{scenario.threats.length - 3}
														{m.more()}
													</div>
												{/if}
											</div>
										</div>
									{/if}

									{#if scenario.qualifications && scenario.qualifications.length > 0}
										<div>
											<h4 class="text-sm font-medium text-gray-900 mb-2">
												<i class="fa-solid fa-tags mr-1"></i>{m.qualifications()} ({scenario
													.qualifications.length})
											</h4>
											<div class="space-y-1">
												{#each scenario.qualifications.slice(0, 3) as qualification}
													<div class="text-sm text-gray-600">• {qualification.name}</div>
												{/each}
												{#if scenario.qualifications.length > 3}
													<div class="text-sm text-gray-500">
														{m.andMore()}
														{scenario.qualifications.length - 3}
														{m.more()}
													</div>
												{/if}
											</div>
										</div>
									{/if}
								</div>

								<!-- Controls Information -->
								{#if scenario.existing_controls?.length > 0 || scenario.additional_controls?.length > 0}
									<div class="px-6 pb-4 border-t border-gray-200">
										<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
											{#if scenario.existing_controls && scenario.existing_controls.length > 0}
												<div>
													<h4 class="text-sm font-medium text-gray-900 mb-3">
														<i class="fa-solid fa-shield-halved mr-1 text-green-600"
														></i>{m.existingControls()}
														({scenario.existing_controls.length})
													</h4>
													<div class="space-y-2">
														{#each scenario.existing_controls as control}
															<div
																class="flex items-center justify-between p-2 bg-green-50 rounded text-sm hover:bg-green-100 transition-colors"
															>
																<div class="flex-1">
																	<Anchor
																		href="/applied-controls/{control.id}"
																		class="font-medium text-green-900 hover:text-green-700 cursor-pointer hover:underline"
																		breadcrumbAction="push"
																	>
																		{control.name}
																	</Anchor>
																	{#if control.category}
																		<span class="text-green-600"> • {control.category}</span>
																	{/if}
																</div>
																<div class="flex items-center space-x-2">
																	<span
																		class="px-2 py-1 bg-green-200 text-green-800 text-xs rounded capitalize"
																	>
																		{safeTranslate(control.status)}
																	</span>
																	<Anchor
																		href="/applied-controls/{control.id}"
																		class="text-green-600 hover:text-green-800 p-1"
																		breadcrumbAction="push"
																		title={m.viewControlDetails()}
																	>
																		<i class="fa-solid fa-external-link text-xs"></i>
																	</Anchor>
																</div>
															</div>
														{/each}
													</div>
												</div>
											{/if}

											{#if scenario.additional_controls && scenario.additional_controls.length > 0}
												<div>
													<h4 class="text-sm font-medium text-gray-900 mb-3">
														<i class="fa-solid fa-plus-circle mr-1 text-blue-600"
														></i>{m.additionalControls()}
														({scenario.additional_controls.length})
													</h4>
													<div class="space-y-2">
														{#each scenario.additional_controls as control}
															<div
																class="flex items-center justify-between p-2 bg-blue-50 rounded text-sm hover:bg-blue-100 transition-colors"
															>
																<div class="flex-1">
																	<Anchor
																		href="/applied-controls/{control.id}"
																		class="font-medium text-blue-900 hover:text-blue-700 cursor-pointer hover:underline"
																		breadcrumbAction="push"
																	>
																		{control.name}
																	</Anchor>
																	{#if control.category}
																		<span class="text-blue-600"> • {control.category}</span>
																	{/if}
																	{#if control.annual_cost && control.annual_cost > 0}
																		<div class="text-xs text-blue-700 mt-1">
																			{m.costYear()}
																			{summaryData.currency}{control.annual_cost.toLocaleString()}{m.costPerYear()}
																		</div>
																	{/if}
																</div>
																<div class="flex items-center space-x-2">
																	<span
																		class="px-2 py-1 bg-blue-200 text-blue-800 text-xs rounded capitalize"
																	>
																		{safeTranslate(control.status)}
																	</span>
																	<Anchor
																		href="/applied-controls/{control.id}"
																		class="text-blue-600 hover:text-blue-800 p-1"
																		breadcrumbAction="push"
																		title={m.viewControlDetails()}
																	>
																		<i class="fa-solid fa-external-link text-xs"></i>
																	</Anchor>
																</div>
															</div>
														{/each}
													</div>
												</div>
											{/if}
										</div>
									</div>
								{/if}
							</div>

							<div class="px-6 pb-6">
								<!-- ALE Insights -->
								<div
									class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 p-4 bg-gray-50 rounded-lg"
								>
									<div class="text-center">
										<div class="text-lg font-bold text-red-600 mb-1">
											{scenario.current_ale_display}
										</div>
										<div class="text-sm text-gray-600">{m.currentAle()}</div>
									</div>
									<div class="text-center">
										<div class="text-lg font-bold text-green-600 mb-1">
											{scenario.residual_ale_display}
										</div>
										<div class="text-sm text-gray-600">{m.residualAle()}</div>
									</div>
									<div class="text-center">
										<div class="text-lg font-bold text-purple-600 mb-1">
											{scenario.risk_reduction_display || m.cannotCalculate()}
										</div>
										<div class="text-sm text-gray-600">{m.riskReduction()}</div>
										<div class="text-xs text-gray-500">{m.currentAle()} - {m.residualAle()}</div>
									</div>
									<div class="text-center">
										<div class="text-lg font-bold text-blue-600 mb-1">
											{scenario.treatment_cost_display || 'N/A'}
										</div>
										<div class="text-sm text-gray-600">{m.treatmentCostDisplay()}</div>
									</div>
								</div>

								<!-- LEC Chart -->
								{#if scenario.lec_curves && scenario.lec_curves.length > 0}
									{@const currentCurve = scenario.lec_curves.find((c) => c.type === 'current')}
									{@const residualCurve = scenario.lec_curves.find((c) => c.type === 'residual')}
									{@const toleranceCurve = scenario.lec_curves.find((c) => c.type === 'tolerance')}

									<div class="bg-white border rounded-lg p-4">
										<h4 class="text-lg font-medium text-gray-900 mb-4">
											{m.lossExceedanceCurve()}
										</h4>
										<div class="w-full">
											<LossExceedanceCurve
												name="scenario-lec-{scenario.id}"
												data={currentCurve?.data || []}
												residualData={residualCurve?.data || []}
												toleranceData={toleranceCurve?.data || []}
												lossThreshold={summaryData.loss_threshold}
												currency={summaryData.currency}
												title={m.scenarioRiskProfile()}
												showTitle={false}
												height="h-80"
												width="w-full"
												enableTooltip={true}
												autoYMax={true}
												autoXMax={true}
												classesContainer="min-w-0"
											/>
										</div>
									</div>
								{:else}
									<div
										class="bg-gray-100 border border-dashed border-gray-300 rounded-lg p-8 text-center"
									>
										<i class="fa-solid fa-chart-area text-3xl text-gray-400 mb-3"></i>
										<p class="text-gray-500">{m.noLecDataAvailableForScenario()}</p>
										<p class="text-sm text-gray-400">
											{m.runSimulationsOnHypotheses()}
										</p>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<!-- No scenarios message -->
				<div class="bg-white rounded-lg p-12 shadow-sm text-center">
					<i class="fa-solid fa-clipboard-list text-4xl text-gray-400 mb-4"></i>
					<h3 class="text-xl font-semibold text-gray-600 mb-2">{m.noSelectedScenarios()}</h3>
					<p class="text-gray-500 mb-4">{m.noScenariosSelectedInStudy()}</p>
					<p class="text-sm text-gray-400">Select scenarios to see the executive summary.</p>
				</div>
			{/if}
		{:else}
			<!-- Error state -->
			<div class="bg-white rounded-lg p-12 shadow-sm text-center">
				<i class="fa-solid fa-exclamation-triangle text-4xl text-red-400 mb-4"></i>
				<h3 class="text-xl font-semibold text-gray-600 mb-2">{m.failedToLoadExecutiveSummary()}</h3>
				<p class="text-gray-500 mb-4">{m.thereWasAnErrorLoadingExecutive()}</p>
				<button class="btn preset-filled-primary-500" onclick={() => window.location.reload()}>
					<i class="fa-solid fa-refresh mr-2"></i>{m.retry()}
				</button>
			</div>
		{/if}
	{:catch error}
		<!-- Error state -->
		<div class="bg-white rounded-lg p-12 shadow-sm text-center">
			<i class="fa-solid fa-exclamation-triangle text-4xl text-red-400 mb-4"></i>
			<h3 class="text-xl font-semibold text-gray-600 mb-2">{m.errorLoadingData()}</h3>
			<p class="text-gray-500 mb-4">
				{error?.message || m.anUnexpectedErrorOccurred()}
			</p>
			<button class="btn preset-filled-primary-500" onclick={() => window.location.reload()}>
				<i class="fa-solid fa-refresh mr-2"></i>{m.retry()}
			</button>
		</div>
	{/await}
</main>

<!-- ALE Breakdown Modal -->
{#if showAleBreakdownModal}
	<div
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
		onclick={(e) => {
			if (e.target === e.currentTarget) showAleBreakdownModal = false;
		}}
	>
		<div class="bg-white rounded-lg p-6 max-w-6xl w-full mx-4 max-h-[90vh] overflow-auto">
			<div class="flex justify-between items-center mb-4">
				<h2 class="text-xl font-semibold">{m.lossBreakdownByScenario()}</h2>
				<button
					onclick={() => (showAleBreakdownModal = false)}
					class="text-gray-500 hover:text-gray-700 text-2xl"
				>
					×
				</button>
			</div>

			{#await data.stream.aleComparison}
				<div class="flex items-center justify-center h-64">
					<div class="text-center">
						<LoadingSpinner />
						<p class="mt-4 text-gray-600">{m.loadingAleComparisonData()}</p>
					</div>
				</div>
			{:then aleComparisonData}
				{#if aleComparisonData?.scenarios && aleComparisonData.scenarios.length > 0}
					<div class="mb-4">
						<ALEComparisonChart
							scenarios={aleComparisonData.scenarios}
							title={m.aleVsTreatmentCostByScenario()}
							height="h-96"
							width="w-full"
						/>
					</div>

					<!-- Summary statistics -->
					<div class="bg-gray-50 rounded-lg p-4 text-sm">
						<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
							<div>
								<div class="font-semibold text-gray-700">{m.totalScenarios()}</div>
								<div class="text-lg font-bold">{aleComparisonData.total_scenarios}</div>
							</div>
							<div>
								<div class="font-semibold text-gray-700">{m.withCurrentAle()}</div>
								<div class="text-lg font-bold text-red-600">
									{aleComparisonData.scenarios_with_current_ale}
								</div>
							</div>
							<div>
								<div class="font-semibold text-gray-700">{m.withResidualAle()}</div>
								<div class="text-lg font-bold text-green-600">
									{aleComparisonData.scenarios_with_residual_ale}
								</div>
							</div>
							<div>
								<div class="font-semibold text-gray-700">{m.withTreatmentCost()}</div>
								<div class="text-lg font-bold text-blue-600">
									{aleComparisonData.scenarios_with_treatment_cost}
								</div>
							</div>
						</div>
					</div>
				{:else}
					<div class="text-center py-8">
						<i class="fa-solid fa-chart-column text-4xl text-gray-400 mb-4"></i>
						<h3 class="text-lg font-semibold text-gray-600 mb-2">{m.noAleDataAvailable()}</h3>
						<p class="text-gray-500">
							{m.runSimulationsToGenerateAle()}
						</p>
					</div>
				{/if}
			{:catch error}
				<div class="text-center py-8">
					<i class="fa-solid fa-exclamation-triangle text-4xl text-red-400 mb-4"></i>
					<h3 class="text-lg font-semibold text-gray-600 mb-2">{m.errorLoadingData()}</h3>
					<p class="text-gray-500">{m.failedToLoadAleComparison()}</p>
				</div>
			{/await}
		</div>
	</div>
{/if}
