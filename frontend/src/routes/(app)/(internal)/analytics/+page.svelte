<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import NightingaleChart from '$lib/components/Chart/NightingaleChart.svelte';
	import Card from '$lib/components/DataViz/Card.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Tab, TabGroup } from '@skeletonlabs/skeleton';
	import ComposerSelect from './ComposerSelect.svelte';
	import CounterCard from './CounterCard.svelte';
	import type { PageData } from './$types';
	import StackedBarsNormalized from '$lib/components/Chart/StackedBarsNormalized.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const risk_assessments = data.risk_assessments;

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

	let tabSet = $state($page.url.searchParams.get('tab')
		? parseInt($page.url.searchParams.get('tab') || '0')
		: 0);

	function handleTabChange(index: number) {
		$page.url.searchParams.set('tab', index.toString());
		goto($page.url);
	}
</script>

<TabGroup class="">
	<Tab bind:group={tabSet} on:click={() => handleTabChange(0)} name="summary" value={0}
		>{m.summary()}</Tab
	>
	<Tab bind:group={tabSet} on:click={() => handleTabChange(1)} name="governance" value={1}
		>{m.governance()}</Tab
	>
	<Tab bind:group={tabSet} on:click={() => handleTabChange(2)} name="risk" value={2}>{m.risk()}</Tab
	>
	<Tab bind:group={tabSet} on:click={() => handleTabChange(3)} name="compliance" value={3}
		>{m.compliance()}</Tab
	>
	{#snippet panel()}
	
			<div class="px-4 pb-4 space-y-8">
				{#if tabSet === 0}
					{#await data.stream.metrics}
						<div class="col-span-3 lg:col-span-1">
							<div>Refreshing data ..</div>
							<LoadingSpinner />
						</div>
					{:then metrics}
						<section id="summary" class=" grid grid-cols-6 gap-2">
							<Card
								count={metrics.controls.total}
								label={m.sumpageTotal()}
								href="/applied-controls/"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								emphasis={true}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.controls.active}
								label={m.sumpageActive()}
								href="/applied-controls/?status=active"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.controls.deprecated}
								label={m.sumpageDeprecated()}
								href="/applied-controls/?status=deprecated"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.controls.to_do}
								label={m.sumpageToDo()}
								href="/applied-controls/?status=to_do"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<div class="h-80 col-span-6 lg:col-span-2 row-span-2 bg-white">
								<NightingaleChart name="nightingale" values={metrics.csf_functions} />
							</div>
							<Card
								count={metrics.controls.in_progress}
								label={m.sumpageInProgress()}
								href="/applied-controls/?status=in_progress"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.controls.on_hold}
								label={m.sumpageOnHold()}
								href="/applied-controls/?status=on_hold"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.controls.p1}
								label={m.sumpageP1()}
								href="/applied-controls/?priority=1&status=to_do&status=deprecated&status=on_hold&status=in_progress&status=--"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								emphasis={true}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.controls.eta_missed}
								label={m.sumpageEtaMissed()}
								href="/applied-controls/?status=to_do&status=deprecated&status=in_progress&status=--&status=on_hold&eta__lte={new Date()
									.toISOString()
									.split('T')[0]}"
								icon="fa-solid fa-shield-halved"
								section={m.sumpageSectionControls()}
								emphasis={true}
								customClass="col-span-3 lg:col-span-1"
							/>
							<div class="col-span-6 lg:col-span-4 row-span-4 bg-white h-96">
								<StackedBarsNormalized
									names={metrics.audits_stats.names}
									data={metrics.audits_stats.data}
									uuids={metrics.audits_stats.uuids}
								/>
							</div>
							<!---->
							<Card
								count={metrics.compliance.used_frameworks}
								label={m.usedFrameworks()}
								href="/frameworks/"
								icon="fa-solid fa-list-check"
								section={m.sumpageSectionCompliance()}
								emphasis={true}
								customClass="col-span-3 lg:col-span-1"
							/>
							<div></div>
							<Card
								count="{metrics.compliance.active_audits}/{metrics.compliance.audits}"
								label={m.sumpageActiveAudits()}
								href="/compliance-assessments/"
								icon="fa-solid fa-list-check"
								section={m.sumpageSectionCompliance()}
								emphasis={true}
								customClass="col-span-3 lg:col-span-1"
							/>

							<Card
								count="{metrics.compliance.progress_avg}%"
								label={m.sumpageAvgProgress()}
								href="/compliance-assessments/"
								icon="fa-solid fa-list-check"
								section={m.sumpageSectionCompliance()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.compliance.non_compliant_items}
								label={m.sumpageNonCompliantItems()}
								href="#"
								icon="fa-solid fa-list-check"
								section={m.sumpageSectionCompliance()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.compliance.evidences}
								label={m.sumpageEvidences()}
								href="/evidences/"
								icon="fa-solid fa-list-check"
								section={m.sumpageSectionCompliance()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<div class=""></div>
							<div class=""></div>
							<!---->
							<div class="col-span-6 lg:col-span-2 row-span-2 h-80 bg-white">
								<HalfDonutChart
									name="current_h"
									title={m.sumpageTitleCurrentRisks()}
									values={data.risks_count_per_level.current}
									colors={data.risks_count_per_level.current.map((object) => object.color)}
								/>
							</div>
							<Card
								count={metrics.risk.assessments}
								label={m.sumpageAssessments()}
								href="/risk-assessments/"
								emphasis={true}
								icon="fa-solid fa-biohazard"
								section={m.sumpageSectionRisk()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<Card
								count={metrics.risk.scenarios}
								label={m.sumpageScenarios()}
								href="/risk-scenarios/"
								icon="fa-solid fa-biohazard"
								section={m.sumpageSectionRisk()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<div class="col-span-6 lg:col-span-2 row-span-2 h-80 bg-white">
								<HalfDonutChart
									name="residual_h"
									title={m.sumpageTitleResidualRisks()}
									values={data.risks_count_per_level.residual}
									colors={data.risks_count_per_level.residual.map((object) => object.color)}
								/>
							</div>
							<Card
								count={metrics.risk.threats}
								label={m.sumpageMappedThreats()}
								href="/analytics?tab=2"
								icon="fa-solid fa-biohazard"
								section={m.sumpageSectionRisk()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<!---->
							<Card
								count={metrics.risk.acceptances}
								label={m.sumpageRiskAccepted()}
								href="/risk-acceptances"
								icon="fa-solid fa-biohazard"
								section={m.sumpageSectionRisk()}
								customClass="col-span-3 lg:col-span-1"
							/>
							<div class=""></div>
						</section>
					{:catch error}
						<div class="col-span-3 lg:col-span-1">
							<p class="text-red-500">Error loading metrics</p>
						</div>
					{/await}
				{:else if tabSet === 1}
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
					{:catch error}
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
									baseEndpoint="/risk-acceptances?to_review=true&approver={$page.data.user.id}"
								/>
							</div>
						</div>
					</section>
				{:else if tabSet === 2}
					<!-- Risk tab -->

					<section>
						{#if data.threats_count.results.labels.length > 0}
							<div class=" h-96 my-2">
								<RadarChart
									name="threatRadar"
									title={m.threatRadarChart()}
									labels={data.threats_count.results.labels}
									values={data.threats_count.results.values}
								/>
							</div>
						{:else}
							<div class="py-4 flex items-center justify-center">
								<p class="">{m.noThreatsMapped()}</p>
							</div>
						{/if}
						<div class="flex flex-wrap lg:flex-nowrap">
							<div class="h-96 flex-col grow lg:flex-1">
								<span class="text-sm font-semibold">{m.currentRiskLevelPerScenario()}</span>

								<DonutChart
									s_label={cur_rsk_label}
									name="current_risk_level"
									values={data.risks_count_per_level.current}
									colors={data.risks_count_per_level.current.map((object) => object.color)}
								/>
							</div>
							<div class="h-96 flex-col grow lg:flex-1">
								<span class="text-sm font-semibold">{m.residualRiskLevelPerScenario()}</span>

								<DonutChart
									s_label={rsd_rsk_label}
									name="residual_risk_level"
									values={data.risks_count_per_level.residual}
									colors={data.risks_count_per_level.residual.map((object) => object.color)}
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
				{:else if tabSet === 3}
					<span class="text-xl font-extrabold"
						><a href="/recap" class="hover:text-purple-500">{m.sectionMoved()}</a></span
					>
					<div class="flex flex-col space-y-2"></div>
				{/if}
			</div>
		
	{/snippet}
</TabGroup>
