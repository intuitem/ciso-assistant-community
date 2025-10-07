<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import GroupedBarChart from '$lib/components/Chart/GroupedBarChart.svelte';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import NightingaleChart from '$lib/components/Chart/NightingaleChart.svelte';
	import StackedBarsNormalized from '$lib/components/Chart/StackedBarsNormalized.svelte';
	import IncidentMonthlyChart from '$lib/components/Chart/IncidentMonthlyChart.svelte';
	import ExceptionSankeyChart from '$lib/components/Chart/ExceptionSankeyChart.svelte';
	import FindingsSankeyChart from '$lib/components/Chart/FindingsSankeyChart.svelte';
	import SunburstChart from '$lib/components/Chart/SunburstChart.svelte';
	import CalendarHeatmap from '$lib/components/Chart/CalendarHeatmap.svelte';
	import Card from '$lib/components/DataViz/Card.svelte';
	import CardGroup from '$lib/components/DataViz/CardGroup.svelte';
	import SimpleCard from '$lib/components/DataViz/SimpleCard.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';
	import CounterCard from './CounterCard.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const cur_rsk_label = m.currentRisk();
	const rsd_rsk_label = m.residualRisk();

	function localizeChartLabels(labels: string[]): string[] {
		return labels.map((label) => safeTranslate(label));
	}

	const appliedControlTodoTable: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			folder: 'domain',
			ranking_score: 'rankingScore',
			eta: 'eta',
			state: 'state'
		},
		body: [],
		meta: []
	};

	const appliedControlWatchlistTable: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			folder: 'domain',
			eta: 'eta',
			expiry_date: 'expiryDate',
			state: 'state'
		},
		body: [],
		meta: []
	};

	const riskAcceptanceWatchlistTable: TableSource = {
		head: {
			name: 'name',
			risk_scenarios: 'riskScenarios',
			expiry_date: 'expiryDate',
			state: 'state'
		},
		body: [],
		meta: []
	};

	let group = $derived(page.url.searchParams.get('tab') || 'summary');

	function handleTabChange(tabValue: string): void {
		page.url.searchParams.set('tab', tabValue);
		goto(page.url);
	}
</script>

<Tabs value={group} onValueChange={(e) => handleTabChange(e.value)}>
	{#snippet list()}
		<Tabs.Control value="summary">{m.summary()}</Tabs.Control>
		<Tabs.Control value="governance">{m.governance()}</Tabs.Control>
		<Tabs.Control value="risk">{m.risk()}</Tabs.Control>
		<Tabs.Control value="compliance">{m.compliance()}</Tabs.Control>
		<Tabs.Control value="operations">{m.operations()}</Tabs.Control>
	{/snippet}
	{#snippet content()}
		{#key group}
			<div class="px-4 pb-4 space-y-8">
				<Tabs.Panel value="summary">
					{#await data.stream.metrics}
						<div class="col-span-3 lg:col-span-1">
							<div>Refreshing data ..</div>
							<LoadingSpinner />
						</div>
					{:then metrics}
						<section id="summary" class="space-y-6">
							<!-- Controls + CSF Functions Row -->
							<div class="grid grid-cols-1 xl:grid-cols-5 gap-6 items-start">
								<!-- Controls Section (3/5 of width) -->
								<div class="xl:col-span-3">
									<CardGroup title={m.sumpageSectionControls()} icon="fa-solid fa-shield-halved">
										<SimpleCard
											count={metrics.controls.total}
											label={m.sumpageTotal()}
											href="/applied-controls/"
											emphasis={true}
										/>
										<SimpleCard
											count={metrics.controls.active}
											label={m.sumpageActive()}
											href="/applied-controls/?status=active"
										/>
										<SimpleCard
											count={metrics.controls.deprecated}
											label={m.sumpageDeprecated()}
											href="/applied-controls/?status=deprecated"
										/>
										<SimpleCard
											count={metrics.controls.to_do}
											label={m.sumpageToDo()}
											href="/applied-controls/?status=to_do"
										/>
										<SimpleCard
											count={metrics.controls.in_progress}
											label={m.sumpageInProgress()}
											href="/applied-controls/?status=in_progress"
										/>
										<SimpleCard
											count={metrics.controls.on_hold}
											label={m.sumpageOnHold()}
											href="/applied-controls/?status=on_hold"
										/>
										<SimpleCard
											count={metrics.controls.p1}
											label={m.sumpageP1()}
											href="/applied-controls/?priority=1&status=to_do&status=deprecated&status=on_hold&status=in_progress&status=--"
											emphasis={true}
										/>
										<SimpleCard
											count={metrics.controls.eta_missed}
											label={m.sumpageEtaMissed()}
											href="/applied-controls/?status=to_do&status=deprecated&status=in_progress&status=--&status=on_hold&eta__lte={new Date()
												.toISOString()
												.split('T')[0]}"
											emphasis={true}
										/>
									</CardGroup>
								</div>

								<!-- CSF Functions Chart (2/5 of width) -->
								<div class="xl:col-span-2">
									<div class="bg-white rounded-lg p-4 h-80 border border-gray-200">
										<NightingaleChart name="nightingale" values={metrics.csf_functions} />
									</div>
								</div>
							</div>
							<!-- Compliance + Audits Chart Row -->
							<div class="grid grid-cols-1 xl:grid-cols-5 gap-6 items-start">
								<!-- Compliance Section (2/5 of width) -->
								<div class="xl:col-span-2">
									<CardGroup
										title={m.sumpageSectionCompliance()}
										icon="fa-solid fa-list-check"
										maxColumns={3}
									>
										<SimpleCard
											count={metrics.compliance.used_frameworks}
											label={m.usedFrameworks()}
											href="/frameworks/"
											emphasis={true}
										/>
										<SimpleCard
											count="{metrics.compliance.active_audits}/{metrics.compliance.audits}"
											label={m.sumpageActiveAudits()}
											href="/compliance-assessments/"
											emphasis={true}
										/>
										<SimpleCard
											count="{metrics.compliance.progress_avg}%"
											label={m.sumpageAvgProgress()}
											href="/compliance-assessments/"
										/>
										<SimpleCard
											count={metrics.compliance.non_compliant_items}
											label={m.sumpageNonCompliantItems()}
											href="#"
										/>
										<SimpleCard
											count={metrics.compliance.evidences}
											label={m.sumpageEvidences()}
											href="/evidences/"
										/>
										<SimpleCard
											count={metrics.compliance.expired_evidences}
											label={m.sumpageExpiredEvidences()}
											href="/evidences/?status=expired"
											emphasis={true}
										/>
									</CardGroup>
								</div>

								<!-- Audits Chart (3/5 of width) -->
								<div class="xl:col-span-3">
									<div class="bg-white rounded-lg p-4 h-96 border border-gray-200">
										<StackedBarsNormalized
											names={metrics.audits_stats.names}
											data={metrics.audits_stats.data}
											uuids={metrics.audits_stats.uuids}
											title={m.recentlyUpdatedAudits()}
										/>
									</div>
								</div>
							</div>
							<!-- Risk Section + Charts Row -->
							<div class="grid grid-cols-1 xl:grid-cols-5 gap-6 items-start">
								<!-- Risk Cards (2/5 of width) -->
								<div class="xl:col-span-2">
									<CardGroup title={m.sumpageSectionRisk()} icon="fa-solid fa-biohazard">
										<SimpleCard
											count={metrics.risk.assessments}
											label={m.sumpageAssessments()}
											href="/risk-assessments/"
											emphasis={true}
										/>
										<SimpleCard
											count={metrics.risk.scenarios}
											label={m.sumpageScenarios()}
											href="/risk-scenarios/"
										/>
										<SimpleCard
											count={metrics.risk.threats}
											label={m.sumpageMappedThreats()}
											href="/analytics?tab=risk"
										/>
										<SimpleCard
											count={metrics.risk.acceptances}
											label={m.sumpageRiskAccepted()}
											href="/risk-acceptances"
										/>
									</CardGroup>
								</div>

								<!-- Risk Charts (3/5 of width) -->
								<div class="xl:col-span-3">
									<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
										<div class="bg-white rounded-lg p-4 h-80 border border-gray-200">
											<HalfDonutChart
												name="current_h"
												title={m.sumpageTitleCurrentRisks()}
												values={data.risks_count_per_level.current}
												colors={data.risks_count_per_level.current.map((object) => object.color)}
											/>
										</div>
										<div class="bg-white rounded-lg p-4 h-80 border border-gray-200">
											<HalfDonutChart
												name="residual_h"
												title={m.sumpageTitleResidualRisks()}
												values={data.risks_count_per_level.residual}
												colors={data.risks_count_per_level.residual.map((object) => object.color)}
											/>
										</div>
									</div>
								</div>
							</div>
						</section>
					{:catch error}
						<div class="col-span-3 lg:col-span-1">
							<p class="text-red-500">Error loading metrics</p>
						</div>
					{/await}
				</Tabs.Panel>
				<Tabs.Panel value="governance">
					{#await data.stream.counters}
						<div class="col-span-3 lg:col-span-1">
							<div>Refreshing data ..</div>
							<LoadingSpinner />
						</div>
					{:then counters}
						<section id="stats" class="mb-6">
							<span class="text-xl font-extrabold">{m.statistics()}</span>
							<div
								class="flex justify-between flex-col lg:flex-row space-y-2 lg:space-y-0 lg:space-x-4"
							>
								<CounterCard
									count={counters.domains}
									label={m.domains()}
									faIcon="fa-solid fa-sitemap"
									href="/folders"
								/>
								<CounterCard
									count={counters.frameworks}
									label={m.frameworks()}
									faIcon="fa-solid fa-book"
									href="/frameworks"
								/>
								<CounterCard
									count={counters.applied_controls}
									label={m.appliedControls()}
									faIcon="fa-solid fa-fire-extinguisher"
									href="/applied-controls"
								/>
								<CounterCard
									count={counters.policies}
									label={m.policies()}
									faIcon="fa-solid fa-file-alt"
									href="/policies"
								/>
								<CounterCard
									count={counters.exceptions}
									label={m.securityExceptions()}
									faIcon="fa-solid fa-circle-exclamation"
									href="/security-exceptions"
								/>
								<CounterCard
									count={counters.risk_acceptances}
									label={m.riskAcceptances()}
									faIcon="fa-solid fa-signature"
									href="/risk-acceptances"
								/>
							</div>
						</section>
					{:catch}
						<div>Data load eror</div>
					{/await}
					{#await data.stream.combinedAssessmentsStatus}
						<div class="col-span-3 lg:col-span-1">
							<div>Loading assessments data...</div>
							<LoadingSpinner />
						</div>
					{:then combinedAssessmentsStatus}
						{#if combinedAssessmentsStatus}
							<section class="bg-white rounded-lg p-4 border border-gray-200 mb-6">
								<GroupedBarChart
									name="combined_assessments_status"
									title={m.assessmentsPerStatus()}
									categories={combinedAssessmentsStatus.status_labels.map((label) =>
										safeTranslate(label)
									)}
									series={combinedAssessmentsStatus.series.map((s) => ({
										name: safeTranslate(s.name),
										data: s.data
									}))}
									height="h-80"
								/>
							</section>
						{/if}
					{:catch}
						<div>Error loading assessments data</div>
					{/await}

					<!-- Calendar Heatmap -->
					{#await data.stream.governanceCalendarData}
						<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
							<h3 class="text-lg font-semibold text-gray-900 mb-4">{m.activityCalendar()}</h3>
							<div class="flex items-center justify-center h-64">
								<LoadingSpinner />
							</div>
						</div>
					{:then calendarData}
						<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
							<h3 class="text-lg font-semibold text-gray-900 mb-4">{m.activityCalendar()}</h3>
							<CalendarHeatmap
								name="governance_activity"
								data={calendarData}
								year={new Date().getFullYear()}
								title=""
								height="h-64"
							/>
						</div>
					{:catch error}
						<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
							<h3 class="text-lg font-semibold text-gray-900 mb-4">{m.activityCalendar()}</h3>
							<div class="flex items-center justify-center h-64 text-gray-500">
								<p>Error loading calendar data</p>
							</div>
						</div>
					{/await}

					<!-- Applied Controls Status and Assessments Status -->
					<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
						<!-- Applied Controls Status Donut -->
						<div class="bg-white rounded-lg p-4 border border-gray-200">
							<h3 class="text-lg font-semibold text-gray-900 mb-4">
								{m.appliedControlsStatus()}
							</h3>
							<div class="h-80">
								{#if data.applied_control_status}
									<DonutChart
										name="applied_controls_status"
										values={data.applied_control_status.values.map((v, i) => ({
											...v,
											name: safeTranslate(data.applied_control_status.labels?.[i] || '')
										}))}
										colors={data.applied_control_status.values?.map((v) => v.itemStyle.color)}
									/>
								{:else}
									<div class="flex items-center justify-center h-full text-gray-500">
										<p>No applied controls data available</p>
									</div>
								{/if}
							</div>
						</div>

						<!-- Findings Assessment Distribution -->
						<div class="bg-white rounded-lg p-4 border border-gray-200">
							<h3 class="text-lg font-semibold text-gray-900 mb-4">
								{m.findingsAssessmentDistribution()}
							</h3>
							<div class="h-80">
								{#await data.stream.findingsAssessmentSunburstData}
									<div class="flex items-center justify-center h-full">
										<LoadingSpinner />
									</div>
								{:then chartData}
									{#if chartData && chartData.length > 0}
										{@const statuses = [
											...new Set(chartData.flatMap((d) => d.children.map((c) => c.name)))
										].map((s) => safeTranslate(s))}
										{@const categoryColors = {
											pentest: '#3b82f6',
											audit: '#10b981',
											self_identified: '#f59e0b',
											'--': '#6b7280'
										}}
										{@const series = chartData.map((category) => ({
											name: safeTranslate(category.name),
											data: statuses.map((status) => {
												const originalStatus = chartData
													.flatMap((d) => d.children)
													.find((c) => safeTranslate(c.name) === status)?.name;
												return category.children.find((c) => c.name === originalStatus)?.value || 0;
											}),
											color: categoryColors[category.name] || '#999'
										}))}
										<GroupedBarChart
											name="findings_assessment_grouped"
											title=""
											categories={statuses}
											{series}
										/>
									{:else}
										<div class="flex items-center justify-center h-full text-gray-500">
											<p>No findings assessment data available</p>
										</div>
									{/if}
								{:catch error}
									<div class="flex items-center justify-center h-full text-red-500">
										<p>Error loading findings assessment data</p>
									</div>
								{/await}
							</div>
						</div>
					</div>

					<!-- Security Exception Flow -->
					{#await data.stream.operationsAnalytics}
						<div class="col-span-3 lg:col-span-1">
							<div>Loading exceptions data...</div>
							<LoadingSpinner />
						</div>
					{:then operationsAnalytics}
						{#if operationsAnalytics}
							<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
								<h3 class="text-lg font-semibold text-gray-900 mb-4">
									{m.securityExceptionFlow()}
								</h3>
								<div class="h-80">
									{#if operationsAnalytics.exception_sankey.nodes.length > 0}
										<ExceptionSankeyChart
											name="exception_sankey"
											title=""
											nodes={operationsAnalytics.exception_sankey.nodes}
											links={operationsAnalytics.exception_sankey.links}
										/>
									{:else}
										<div class="flex items-center justify-center h-full text-gray-500">
											<p>{m.noExceptionData()}</p>
										</div>
									{/if}
								</div>
							</div>
						{/if}
					{:catch}
						<div>Error loading exceptions data</div>
					{/await}
				</Tabs.Panel>
				<Tabs.Panel value="risk">
					<!-- Risk tab -->

					<section>
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
							{#if data.threats_count.results.labels.length > 0}
								<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
									<h3 class="text-lg font-semibold text-gray-900 mb-2">
										{m.threatRadarChart()}
									</h3>
									<div class="h-96">
										<RadarChart
											name="threatRadar"
											title=""
											labels={data.threats_count.results.labels}
											values={data.threats_count.results.values}
										/>
									</div>
								</div>
							{:else}
								<div
									class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex items-center justify-center"
								>
									<p class="text-gray-500">{m.noThreatsMapped()}</p>
								</div>
							{/if}
							{#if data.qualifications_count.results.labels.length > 0}
								<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
									<h3 class="text-lg font-semibold text-gray-900 mb-4">
										{m.qualificationsChartTitle()}
									</h3>
									<div class="h-80">
										<BarChart
											name="qualificationsBar"
											title=""
											labels={localizeChartLabels(data.qualifications_count.results.labels)}
											values={data.qualifications_count.results.values}
											horizontal={true}
										/>
									</div>
								</div>
							{:else}
								<div
									class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex items-center justify-center"
								>
									<p class="text-gray-500">{m.noQualificationsFoundOnRiskScenarios()}</p>
								</div>
							{/if}
						</div>
						<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
							<div class="flex flex-wrap lg:flex-nowrap gap-6">
								{#if page.data?.featureflags?.inherent_risk}
									<div class="h-96 flex-col grow lg:flex-1">
										<span class="text-sm font-semibold">{m.inherentRiskLevelPerScenario()}</span>

										<DonutChart
											s_label={m.inherentRisk()}
											name="inherent_risk_level"
											values={data.risks_count_per_level.inherent}
											colors={data.risks_count_per_level.inherent?.map((object) => object.color)}
										/>
									</div>
								{/if}
								<div class="h-96 flex-col grow lg:flex-1">
									<span class="text-sm font-semibold">{m.currentRiskLevelPerScenario()}</span>

									<DonutChart
										s_label={cur_rsk_label}
										name="current_risk_level"
										values={data.risks_count_per_level.current}
										colors={data.risks_count_per_level.current?.map((object) => object.color)}
									/>
								</div>
								<div class="h-96 flex-col grow lg:flex-1">
									<span class="text-sm font-semibold">{m.residualRiskLevelPerScenario()}</span>

									<DonutChart
										s_label={rsd_rsk_label}
										name="residual_risk_level"
										values={data.risks_count_per_level.residual}
										colors={data.risks_count_per_level.residual?.map((object) => object.color)}
									/>
								</div>
							</div>
						</div>
						<!-- Vulnerability Sankey -->
						{#await data.stream.vulnerabilitySankeyData}
							<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
								<h3 class="text-lg font-semibold text-gray-900 mb-4">
									{m.vulnerabilityDistribution()}
								</h3>
								<div class="flex items-center justify-center h-80">
									<LoadingSpinner />
								</div>
							</div>
						{:then sankeyData}
							{#if sankeyData && sankeyData.length > 0}
								<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
									<h3 class="text-lg font-semibold text-gray-900 mb-4">
										{m.vulnerabilityDistribution()}
									</h3>
									<div class="h-96">
										{#await import('$lib/components/Chart/VulnerabilitySankeyChart.svelte')}
											<LoadingSpinner />
										{:then { default: VulnerabilitySankeyChart }}
											<VulnerabilitySankeyChart {sankeyData} />
										{/await}
									</div>
								</div>
							{/if}
						{:catch error}
							<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
								<h3 class="text-lg font-semibold text-gray-900 mb-4">
									{m.vulnerabilityDistribution()}
								</h3>
								<div class="flex items-center justify-center h-80 text-gray-500">
									<p>{m.errorLoadingVulnerabilityData()}</p>
								</div>
							</div>
						{/await}
					</section>
				</Tabs.Panel>
				<Tabs.Panel value="compliance">
					<section class="space-y-6">
						<div class="flex justify-between items-center mb-6">
							<h2 class="text-xl font-bold text-gray-900">{m.complianceAnalytics()}</h2>
							<a
								href="/recap"
								class="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 hover:border-blue-300 transition-colors"
							>
								{m.viewDetailedRecap()}
								<i class="fas fa-arrow-right text-xs"></i>
							</a>
						</div>

						{#if data.complianceAnalytics && Object.keys(data.complianceAnalytics).length > 0}
							<div class="space-y-6">
								{#each Object.entries(data.complianceAnalytics) as [frameworkName, frameworkData]}
									<div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
										<!-- Framework Header -->
										<div
											class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-100"
										>
											<div class="flex justify-between items-center">
												<div class="flex items-center gap-3">
													<div class="w-2 h-2 bg-blue-500 rounded-full"></div>
													<h3 class="text-lg font-semibold text-gray-900">{frameworkName}</h3>
												</div>
												<div class="flex items-center gap-2">
													<span class="text-sm text-gray-600">{m.averageProgress()}:</span>
													<div
														class="flex items-center gap-2 px-3 py-1 bg-white rounded-full shadow-sm"
													>
														<div class="w-32 bg-gray-200 rounded-full h-1.5">
															<div
																class="bg-gradient-to-r from-blue-500 to-indigo-500 h-1.5 rounded-full transition-all duration-500"
																style="width: {frameworkData.framework_average}%"
															></div>
														</div>
														<span class="font-semibold text-blue-600 text-sm min-w-[2.5rem]">
															{frameworkData.framework_average}%
														</span>
													</div>
												</div>
											</div>
										</div>

										<!-- Domains -->
										<div class="p-6 space-y-5">
											{#each frameworkData.domains as domain}
												<div class="relative">
													<!-- Domain Header -->
													<div
														class="flex justify-between items-center mb-3 pb-2 border-b border-gray-100"
													>
														<div class="flex items-center gap-2">
															<i class="fas fa-folder text-amber-500 text-sm"></i>
															<h4 class="font-medium text-gray-800">{domain.domain}</h4>
														</div>
														<div class="flex items-center gap-2">
															<span class="text-xs text-gray-500">{m.averageProgress()}:</span>
															<div class="flex items-center gap-2">
																<div class="w-8 bg-gray-200 rounded-full h-1">
																	<div
																		class="bg-gradient-to-r from-amber-400 to-orange-500 h-1 rounded-full transition-all duration-300"
																		style="width: {domain.domain_average}%"
																	></div>
																</div>
																<span class="font-medium text-amber-600 text-xs">
																	{domain.domain_average}%
																</span>
															</div>
														</div>
													</div>

													<!-- Assessments Grid -->
													<div class="grid gap-3">
														{#each domain.assessments as assessment}
															<div
																class="group border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all duration-200"
															>
																<div class="flex justify-between items-start gap-4">
																	<div class="flex-1 min-w-0">
																		<div class="font-medium text-gray-900 mb-1 truncate">
																			{assessment.assessment_name}
																		</div>
																		<div class="flex items-center gap-3 text-xs text-gray-500">
																			<div class="flex items-center gap-1">
																				<i class="fas fa-cubes text-gray-400"></i>
																				<span>{assessment.perimeter}</span>
																			</div>
																			<div class="flex items-center gap-1">
																				<div
																					class="w-2 h-2 rounded-full {assessment.status === 'done'
																						? 'bg-green-400'
																						: assessment.status === 'in_progress'
																							? 'bg-blue-400'
																							: assessment.status === 'in_review'
																								? 'bg-yellow-400'
																								: 'bg-gray-400'}"
																				></div>
																				<span class="capitalize"
																					>{assessment.status?.replace('_', ' ') ||
																						'No status'}</span
																				>
																			</div>
																		</div>
																	</div>
																	<div class="flex items-center gap-3">
																		<!-- Progress Bar -->
																		<div class="flex items-center gap-2">
																			<div class="w-20 bg-gray-200 rounded-full h-2">
																				<div
																					class="h-2 rounded-full transition-all duration-500 {assessment.progress >=
																					80
																						? 'bg-gradient-to-r from-green-400 to-emerald-500'
																						: assessment.progress >= 50
																							? 'bg-gradient-to-r from-blue-400 to-cyan-500'
																							: assessment.progress >= 25
																								? 'bg-gradient-to-r from-yellow-400 to-orange-500'
																								: 'bg-gradient-to-r from-red-400 to-pink-500'}"
																					style="width: {assessment.progress}%"
																				></div>
																			</div>
																			<span
																				class="font-semibold text-sm min-w-[3rem] text-right {assessment.progress >=
																				80
																					? 'text-green-600'
																					: assessment.progress >= 50
																						? 'text-blue-600'
																						: assessment.progress >= 25
																							? 'text-orange-600'
																							: 'text-red-600'}"
																			>
																				{assessment.progress}%
																			</span>
																		</div>
																	</div>
																</div>
															</div>
														{/each}
													</div>
												</div>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<div
								class="text-center py-16 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border-2 border-dashed border-gray-300"
							>
								<div class="text-gray-400 mb-4">
									<i class="fas fa-chart-bar text-6xl"></i>
								</div>
								<div class="text-gray-600">
									<p class="text-xl font-semibold mb-2">{m.noComplianceData()}</p>
									<p class="text-sm text-gray-500">{m.createComplianceAssessment()}</p>
								</div>
								<a
									href="/compliance-assessments"
									class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
								>
									<i class="fas fa-plus text-sm"></i>
									{m.createAssessment()}
								</a>
							</div>
						{/if}
					</section>
				</Tabs.Panel>
				<Tabs.Panel value="operations">
					{#await data.stream.operationsAnalytics}
						<div class="col-span-3 lg:col-span-1">
							<div>Refreshing data ..</div>
							<LoadingSpinner />
						</div>
					{:then operationsAnalytics}
						{#if operationsAnalytics}
							<section class="space-y-6">
								<!-- First Row: Applied Controls Sunburst and Task Templates Status -->
								<div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
									<!-- Applied Controls Sunburst (2/3 width) -->
									<div
										class="xl:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6"
									>
										<h3 class="text-lg font-semibold text-gray-900 mb-4">
											{m.appliedControlsDistribution()}
										</h3>
										<div class="h-96">
											{#if operationsAnalytics.applied_controls_sunburst && operationsAnalytics.applied_controls_sunburst.length > 0}
												<SunburstChart
													name="applied_controls_sunburst"
													title=""
													data={operationsAnalytics.applied_controls_sunburst}
												/>
											{:else}
												<div class="flex items-center justify-center h-full text-gray-500">
													<p>No applied controls data available</p>
												</div>
											{/if}
										</div>
									</div>

									<!-- Task Templates Status Donut (1/3 width) -->
									<div
										class="xl:col-span-1 bg-white rounded-xl shadow-sm border border-gray-200 p-6"
									>
										<h3 class="text-lg font-semibold text-gray-900 mb-4">
											{m.tasksStatus()}
										</h3>
										<div class="h-96">
											{#if data.task_template_status}
												<DonutChart
													name="task_templates_status"
													values={data.task_template_status.values.map((v, i) => ({
														...v,
														localName: data.task_template_status.localLables[i]
													}))}
													colors={data.task_template_status.values?.map((v) => v.itemStyle.color)}
												/>
											{:else}
												<div class="flex items-center justify-center h-full text-gray-500">
													<p>No tasks data available</p>
												</div>
											{/if}
										</div>
									</div>
								</div>

								<!-- Second Row: Findings Breakdown Sankey -->
								<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
									<h3 class="text-lg font-semibold text-gray-900 mb-4">
										{m.findingsBreakdown()}
									</h3>
									<div class="h-80">
										{#if operationsAnalytics.findings_sankey && operationsAnalytics.findings_sankey.nodes && operationsAnalytics.findings_sankey.nodes.length > 0}
											<FindingsSankeyChart
												name="findings_sankey"
												title=""
												nodes={operationsAnalytics.findings_sankey.nodes}
												links={operationsAnalytics.findings_sankey.links}
											/>
										{:else}
											<div class="flex items-center justify-center h-full text-gray-500">
												<p>{m.noFindingsData()}</p>
											</div>
										{/if}
									</div>
								</div>

								<!-- Third Row: Incident Summary Cards -->
								<div class="grid grid-cols-1 xl:grid-cols-1 gap-6 items-start">
									<!-- Summary Cards (full width) -->
									<div class="xl:col-span-1">
										<CardGroup title={m.incidentSummary()} icon="fa-solid fa-chart-simple">
											<SimpleCard
												count={operationsAnalytics.summary_stats.total_incidents}
												label={m.totalIncidents()}
												href="/incidents/"
												emphasis={true}
											/>
											<SimpleCard
												count={operationsAnalytics.summary_stats.incidents_this_month}
												label={m.incidentsThisMonth()}
												href="/incidents/"
												emphasis={true}
											/>
											<SimpleCard
												count={operationsAnalytics.summary_stats.open_incidents}
												label={m.openIncidents()}
												href="/incidents/?status=new&status=ongoing&status=resolved"
												emphasis={true}
											/>
										</CardGroup>
									</div>
								</div>

								<!-- Third Row: Severity Breakdown and Qualifications Radar -->
								<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
									<!-- Severity Breakdown Chart -->
									<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
										<h3 class="text-lg font-semibold text-gray-900 mb-4">
											{m.incidentSeverityBreakdown()}
										</h3>
										<div class="h-80">
											<DonutChart
												name="incident_severity"
												values={operationsAnalytics.severity_breakdown}
											/>
										</div>
									</div>

									<!-- Qualifications Radar Chart -->
									<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
										<h3 class="text-lg font-semibold text-gray-900 mb-4">
											{m.incidentQualificationsRadar()}
										</h3>
										<div class="h-80">
											{#if operationsAnalytics.qualifications_breakdown.labels.length > 0}
												<RadarChart
													name="incident_qualifications"
													title=""
													labels={operationsAnalytics.qualifications_breakdown.labels}
													values={operationsAnalytics.qualifications_breakdown.values}
												/>
											{:else}
												<div class="flex items-center justify-center h-full text-gray-500">
													<p>{m.noQualificationsData()}</p>
												</div>
											{/if}
										</div>
									</div>
								</div>

								<!-- Fourth Row: Monthly Metrics and Detection Breakdown -->
								<div class="grid grid-cols-1 xl:grid-cols-5 gap-6 items-start">
									<!-- Monthly Incident Metrics (3/5 of width) -->
									<div class="xl:col-span-3">
										<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
											<h3 class="text-lg font-semibold text-gray-900 mb-4">
												{m.monthlyIncidentMetrics()}
											</h3>
											<div class="h-80">
												<IncidentMonthlyChart
													name="incident_monthly"
													title=""
													months={operationsAnalytics.monthly_metrics.months}
													monthlyCount={operationsAnalytics.monthly_metrics.monthly_counts}
													cumulativeCount={operationsAnalytics.monthly_metrics.cumulative_counts}
												/>
											</div>
										</div>
									</div>

									<!-- Detection Breakdown Chart (2/5 of width) -->
									<div class="xl:col-span-2">
										<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
											<h3 class="text-lg font-semibold text-gray-900 mb-4">
												{m.incidentDetectionBreakdown()}
											</h3>
											<div class="h-80">
												<DonutChart
													name="incident_detection"
													values={operationsAnalytics.incident_detection_breakdown}
													colors={['#3B82F6', '#EF4444']}
												/>
											</div>
										</div>
									</div>
								</div>
							</section>
						{:else}
							<div
								class="text-center py-16 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border-2 border-dashed border-gray-300"
							>
								<div class="text-gray-400 mb-4">
									<i class="fas fa-exclamation-triangle text-6xl"></i>
								</div>
								<div class="text-gray-600">
									<p class="text-xl font-semibold mb-2">{m.noOperationsData()}</p>
									<p class="text-sm text-gray-500">{m.createIncidents()}</p>
								</div>
								<a
									href="/incidents"
									class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
								>
									<i class="fas fa-plus text-sm"></i>
									{m.createIncident()}
								</a>
							</div>
						{/if}
					{:catch error}
						<div
							class="text-center py-16 bg-gradient-to-br from-red-50 to-red-100 rounded-xl border-2 border-dashed border-red-300"
						>
							<div class="text-red-400 mb-4">
								<i class="fas fa-exclamation-triangle text-6xl"></i>
							</div>
							<div class="text-red-600">
								<p class="text-xl font-semibold mb-2">Error loading operations data</p>
								<p class="text-sm text-red-500">Please try refreshing the page</p>
							</div>
						</div>
					{/await}
				</Tabs.Panel>
			</div>
		{/key}
	{/snippet}
</Tabs>
