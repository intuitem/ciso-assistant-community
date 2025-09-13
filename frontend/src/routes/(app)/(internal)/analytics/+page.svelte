<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import NightingaleChart from '$lib/components/Chart/NightingaleChart.svelte';
	import StackedBarsNormalized from '$lib/components/Chart/StackedBarsNormalized.svelte';
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
						<section id="stats">
							<span class="text-xl font-extrabold">{m.statistics()}</span>
							<div
								class="flex justify-between flex-col lg:flex-row space-y-2 lg:space-y-0 lg:space-x-4"
							>
								<CounterCard
									count={counters.domains}
									label={m.domains()}
									faIcon="fa-solid fa-diagram-project"
									href="/folders"
								/>
								<CounterCard
									count={counters.perimeters}
									label={m.perimeters()}
									faIcon="fa-solid fa-cubes"
									href="/perimeters"
								/>
								<CounterCard
									count={counters.applied_controls}
									label={m.appliedControls()}
									faIcon="fa-solid fa-fire-extinguisher"
									href="/applied-controls"
								/>
								<CounterCard
									count={counters.risk_assessments}
									label={m.riskAssessments()}
									faIcon="fa-solid fa-magnifying-glass-chart"
									href="/risk-assessments"
								/>
								<CounterCard
									count={counters.compliance_assessments}
									label={m.complianceAssessments()}
									faIcon="fa-solid fa-arrows-to-eye"
									href="/compliance-assessments"
								/>
								<CounterCard
									count={counters.policies}
									label={m.policies()}
									faIcon="fas fa-file-alt"
									href="/policies"
								/>
							</div>
						</section>
					{:catch}
						<div>Data load eror</div>
					{/await}
					<section class="space-y-4">
						<div
							class="flex flex-col lg:flex-row space-y-2 lg:space-y-0 lg:space-x-4 h-96 lg:h-48 text-sm whitespace-nowrap"
						>
							<BarChart
								classesContainer="flex-1 card p-4 bg-white"
								name="complianceAssessmentsPerStatus"
								title={m.complianceAssessmentsStatus()}
								labels={localizeChartLabels(data.complianceAssessmentsPerStatus.localLables)}
								values={data.complianceAssessmentsPerStatus.values}
							/>
							<BarChart
								classesContainer="basis-1/2 card p-4 bg-white"
								name="usedFrameworks"
								horizontal
								title={m.usedFrameworks()}
								labels={data.usedFrameworks.map((framework) =>
									framework.name.length > 60
										? `${framework.name.substring(0, 60)}...`
										: framework.name
								)}
								values={data.usedFrameworks.map(
									(framework) => framework.compliance_assessments_count
								)}
							/>
						</div>
						<div
							class="flex flex-col lg:flex-row space-y-2 lg:space-y-0 lg:space-x-4 h-96 lg:h-48 text-sm whitespace-nowrap"
						>
							<BarChart
								classesContainer="flex-1 card p-4 bg-white"
								name="riskAssessmentsPerStatus"
								title={m.riskAssessmentsStatus()}
								labels={localizeChartLabels(data.riskAssessmentsPerStatus.localLables)}
								values={data.riskAssessmentsPerStatus.values}
							/>
							<DonutChart
								classesContainer="flex-1 card p-4 bg-white"
								name="riskScenariosStatus"
								title={m.riskScenariosStatus()}
								values={data.riskScenariosPerStatus.values}
								orientation="horizontal"
							/>
						</div>
					</section>
					<section class="card p-4 bg-white">
						<div>
							<div class="text-xl font-extrabold">{m.pendingMeasures()}</div>
							<div class="text-sm text-gray-500">
								{m.orderdByRankingScore()}
							</div>
							<ModelTable
								URLModel="applied-controls"
								source={appliedControlTodoTable}
								fields={[
									'name',
									'category',
									'csf_function',
									'folder',
									'ranking_score',
									'eta',
									'state'
								]}
								hideFilters={true}
								search={false}
								rowsPerPage={false}
								orderBy={{ identifier: 'ranking_score', direction: 'desc' }}
								baseEndpoint="/applied-controls?todo=true"
							/>
							<div class="text-sm">
								<i class="fa-solid fa-info-circle"></i>
								{m.rankingScoreDefintion()}.
							</div>
						</div>
					</section>
					<section class="space-y-2 card p-4 bg-white">
						<div>
							<div class="text-xl font-extrabold">{m.watchlist()}</div>
							<div class="text-sm text-gray-500">
								{m.watchlistDescription()}
							</div>
						</div>
						<div class="flex flex-col space-y-5 items-center content-center">
							<div class="w-full">
								<span class="text-md font-semibold">{m.measuresToReview()}</span>
								<ModelTable
									source={appliedControlWatchlistTable}
									URLModel="applied-controls"
									hideFilters={true}
									search={false}
									rowsPerPage={false}
									fields={[
										'name',
										'category',
										'csf_function',
										'folder',
										'eta',
										'expiry_date',
										'state'
									]}
									baseEndpoint="/applied-controls?to_review=true"
								/>
							</div>
							<div class="w-full">
								<span class="text-md font-semibold">{m.acceptancesToReview()}</span>
								<ModelTable
									source={riskAcceptanceWatchlistTable}
									URLModel="risk-acceptances"
									hideFilters={true}
									search={false}
									rowsPerPage={false}
									fields={['name', 'risk_scenarios', 'expiry_date', 'state']}
									baseEndpoint="/risk-acceptances?to_review=true&approver={page.data.user.id}"
								/>
							</div>
						</div>
					</section>
				</Tabs.Panel>
				<Tabs.Panel value="risk">
					<!-- Risk tab -->

					<section>
						<div class="flex flex-col lg:flex-row space-y-4 lg:space-y-0 lg:space-x-4 h-96 my-2">
							{#if data.threats_count.results.labels.length > 0}
								<div class="flex-1 card p-4 bg-white">
									<RadarChart
										name="threatRadar"
										title={m.threatRadarChart()}
										labels={data.threats_count.results.labels}
										values={data.threats_count.results.values}
									/>
								</div>
							{:else}
								<div class="flex-1 card p-4 bg-white flex items-center justify-center">
									<p class="">{m.noThreatsMapped()}</p>
								</div>
							{/if}
							{#if data.qualifications_count.results.labels.length > 0}
								<div class="flex-1 card p-4 bg-white">
									<BarChart
										name="qualificationsBar"
										title={m.qualificationsChartTitle()}
										labels={localizeChartLabels(data.qualifications_count.results.labels)}
										values={data.qualifications_count.results.values}
										horizontal={true}
									/>
								</div>
							{:else}
								<div class="flex-1 card p-4 bg-white flex items-center justify-center">
									<p class="">No qualifications found on risk scenarios</p>
								</div>
							{/if}
						</div>
						<div class="flex flex-wrap lg:flex-nowrap">
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
						<div class="h-96">
							<BarChart
								name="mtg"
								title={m.appliedControlsStatus()}
								labels={data.applied_control_status.labels}
								values={data.applied_control_status.values}
							/>
						</div>
					</section>
				</Tabs.Panel>
				<Tabs.Panel value="compliance">
					<span class="text-xl font-extrabold"
						><a href="/recap" class="hover:text-purple-500">{m.sectionMoved()}</a></span
					>
					<div class="flex flex-col space-y-2"></div>
				</Tabs.Panel>
			</div>
		{/key}
	{/snippet}
</Tabs>
