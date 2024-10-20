<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import TreemapChart from '$lib/components/Chart/TreemapChart.svelte';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import NightingaleChart from '$lib/components/Chart/NightingaleChart.svelte';
	import Card from '$lib/components/DataViz/Card.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { localItems } from '$lib/utils/locales.js';
	import * as m from '$paraglide/messages';
	import { languageTag } from '$paraglide/runtime';
	import { ProgressRadial, Tab, TabGroup, tableSourceMapper } from '@skeletonlabs/skeleton';
	import ComposerSelect from './ComposerSelect.svelte';
	import CounterCard from './CounterCard.svelte';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import type { PageData } from './$types';

	interface Counters {
		domains: number;
		projects: number;
		applied_controls: number;
		risk_assessments: number;
		compliance_assessments: number;
		policies: number;
	}

	export let data: PageData;

	const counters: Counters = data.get_counters;
	const metrics = data.metrics;
	const risk_assessments = data.risk_assessments;

	const cur_rsk_label = m.currentRisk();
	const rsd_rsk_label = m.residualRisk();

	function localizeChartLabels(labels: string[]): string[] {
		return labels.map((label) => localItems()[label]);
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
		body: tableSourceMapper(data.measures, [
			'name',
			'category',
			'csf_function',
			'folder',
			'ranking_score',
			'eta',
			'state'
		]),
		meta: data.measures
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
		body: tableSourceMapper(data.measures_to_review, [
			'name',
			'category',
			'csf_function',
			'folder',
			'eta',
			'expiry_date',
			'state'
		]),
		meta: data.measures_to_review
	};

	const riskAcceptanceWatchlistTable: TableSource = {
		head: {
			name: 'name',
			risk_scenarios: 'riskScenarios',
			expiry_date: 'expiryDate',
			state: 'state'
		},
		body: tableSourceMapper(data.acceptances_to_review, [
			'name',
			'risk_scenarios',
			'expiry_date',
			'state'
		]),
		meta: data.acceptances_to_review
	};

	let tabSet = $page.url.searchParams.get('tab')
		? parseInt($page.url.searchParams.get('tab') || '0')
		: 0;

	function handleTabChange(index: number) {
		$page.url.searchParams.set('tab', index.toString());
		goto($page.url);
	}

	const REQUIREMENT_ASSESSMENT_STATUS = [
		'compliant',
		'partially_compliant',
		'in_progress',
		'non_compliant',
		'not_applicable',
		'to_do'
	] as const;
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
	<Tab bind:group={tabSet} on:click={() => handleTabChange(4)} name="composer" value={4}
		>{m.composer()}</Tab
	>
	<svelte:fragment slot="panel">
		<div class="px-4 pb-4 space-y-8">
			{#if tabSet === 0}
				<section id="summary" class=" grid grid-cols-6 gap-4">
					<Card
						count={metrics.controls.total}
						label="total"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-shield-halved"
						section="controls"
						emphasis={true}
					/>
					<Card
						count={metrics.controls.active}
						label="active"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-shield-halved"
						section="controls"
					/>
					<Card
						count={metrics.controls.deprecated}
						label="deprecated"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-shield-halved"
						section="controls"
					/>
					<div class="h-64 col-span-3 row-span-2 bg-white">
						<NightingaleChart name="nightingale" values={metrics.csf_functions} />
					</div>
					<Card
						count={metrics.controls.to_do}
						label="to do"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-shield-halved"
						section="controls"
					/>
					<Card
						count={metrics.controls.in_progress}
						label="in progress"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-shield-halved"
						section="controls"
					/>
					<Card
						count={metrics.controls.on_hold}
						label="on hold"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-shield-halved"
						section="controls"
					/>
					<div class="col-span-4 row-span-4 bg-white">
						<TreemapChart title="Compliance overview" tree={metrics.audits_tree} name="sunburst" />
					</div>
					<!---->
					<Card
						count="{metrics.compliance.active_audits}/{metrics.compliance.audits}"
						label="active audits"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-list-check"
						section="compliance"
						emphasis={true}
					/>
					<div></div>
					<Card
						count={metrics.compliance.compliant_items}
						label="compliant items"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-list-check"
						section="compliance"
					/>
					<Card
						count={metrics.compliance.non_compliant_items}
						label="non compliant items"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-list-check"
						section="compliance"
					/>
					<Card
						count={metrics.compliance.evidences}
						label="evidences"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-list-check"
						section="compliance"
					/>
					<div class=""></div>
					<div class=""></div>
					<!---->
					<div class=" col-span-2 row-span-2 h-80 bg-white">
						<HalfDonutChart
							name="current_h"
							title="Current risks"
							values={data.risks_count_per_level.current}
							colors={data.risks_count_per_level.current.map((object) => object.color)}
						/>
					</div>
					<Card
						count={metrics.risk.assessments}
						label="assessments"
						href="#"
						help="this is interesting"
						emphasis={true}
						icon="fa-solid fa-biohazard"
						section="risk"
					/>
					<Card
						count={metrics.risk.scenarios}
						label="scenarios"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-biohazard"
						section="risk"
					/>
					<div class=" col-span-2 row-span-2 bg-white">
						<HalfDonutChart
							name="residual_h"
							title="Residual risks"
							values={data.risks_count_per_level.residual}
							colors={data.risks_count_per_level.residual.map((object) => object.color)}
						/>
					</div>
					<Card
						count={metrics.risk.threats}
						label="mapped threats"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-biohazard"
						section="risk"
					/>
					<!---->
					<Card
						count={metrics.risk.acceptances}
						label="risks accepted"
						href="#"
						help="this is interesting"
						icon="fa-solid fa-biohazard"
						section="risk"
					/>
					<div class=""></div>
				</section>
			{:else if tabSet === 1}
				<section id="stats">
					<span class="text-xl font-extrabold">{m.statistics()}</span>
					<div class="flex justify-between space-x-4">
						<CounterCard
							count={counters.domains}
							label={m.domains()}
							faIcon="fa-solid fa-diagram-project"
							href="/folders"
						/>
						<CounterCard
							count={counters.projects}
							label={m.projects()}
							faIcon="fa-solid fa-cubes"
							href="/projects"
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
				<section class="space-y-4">
					<div class="flex flex-row space-x-4 h-48 text-sm whitespace-nowrap">
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
					<div class="flex flex-row space-x-4 h-48 text-sm whitespace-nowrap">
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
							hideFilters={true}
							search={false}
							rowsPerPage={false}
							orderBy={{ identifier: 'ranking_score', direction: 'desc' }}
						/>
						<div class="text-sm">
							<i class="fa-solid fa-info-circle" />
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
							/>
						</div>
						<div class="w-full">
							<span class="text-md font-semibold">{m.exceptionsToReview()}</span>
							<ModelTable
								source={riskAcceptanceWatchlistTable}
								URLModel="risk-acceptances"
								hideFilters={true}
								search={false}
								rowsPerPage={false}
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
					<div class="flex">
						<div class="h-96 flex-1">
							<span class="text-sm font-semibold">{m.currentRiskLevelPerScenario()}</span>

							<DonutChart
								s_label={cur_rsk_label}
								name="current_risk_level"
								values={data.risks_count_per_level.current}
								colors={data.risks_count_per_level.current.map((object) => object.color)}
							/>
						</div>
						<div class="h-96 flex-1">
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
				<span class="text-xl font-extrabold">{m.overallCompliance()}</span>
				<div class="flex flex-col space-y-2">
					{#each data.projects as project}
						<div class="flex flex-col items-center">
							{#if project.compliance_assessments && project.compliance_assessments.length > 0}
								<div class="flex flex-row space-x-2 w-1/2 justify-between items-center">
									<a
										class="text-xl font-bold mb-1 hover:underline text-primary-600"
										href="/projects/{project.id}">{project.folder.str}/{project.name}</a
									>
									<div class="flex flex-1 bg-gray-200 rounded-full overflow-hidden h-4 shrink">
										{#each project.overallCompliance.values.sort((a, b) => REQUIREMENT_ASSESSMENT_STATUS.indexOf(a.name) - REQUIREMENT_ASSESSMENT_STATUS.indexOf(b.name)) as sp}
											<div
												class="flex flex-col justify-center overflow-hidden text-black text-xs text-center"
												style="width: {sp.percentage}%; background-color: {sp.itemStyle.color}"
											>
												{sp.percentage}%
											</div>
										{/each}
									</div>
								</div>
							{/if}

							{#each project.compliance_assessments as compliance_assessment}
								<div class="card w-full bg-white flex flex-row mx-8 p-4 relative">
									<div class="w-1/5 flex flex-col space-y-2">
										<div>
											<p class="text-sm font-semibold">{m.name()}</p>
											<a class="anchor" href="compliance-assessments/{compliance_assessment.id}"
												>{compliance_assessment.name}</a
											>
										</div>
										<div>
											<p class="text-sm font-semibold">{m.framework()}</p>
											<p>{compliance_assessment.framework.str}</p>
										</div>
									</div>
									{#if compliance_assessment.globalScore.score >= 0}
										<div class="justify-center flex items-center">
											<ProgressRadial
												stroke={100}
												meter={displayScoreColor(
													compliance_assessment.globalScore.score,
													compliance_assessment.globalScore.max_score
												)}
												value={formatScoreValue(
													compliance_assessment.globalScore.score,
													compliance_assessment.globalScore.max_score
												)}
												font={150}
												width={'w-20'}>{compliance_assessment.globalScore.score}</ProgressRadial
											>
										</div>
									{/if}
									<div class="w-3/5 h-32">
										<DonutChart
											s_label={m.complianceAssessments()}
											name={compliance_assessment.name + '_donut'}
											values={compliance_assessment.donut.result.values}
										/>
									</div>
									<div class="absolute top-2 right-4 mt-2 space-x-1">
										<div class="flex flex-col space-y-1">
											<a
												href="/compliance-assessments/{compliance_assessment.id}/edit?next=/analytics?tab=3"
												class="btn variant-filled-primary"
												><i class="fa-solid fa-edit mr-2" /> {m.edit()}
											</a>
											<a
												href="/compliance-assessments/{compliance_assessment.id}/export"
												class="btn variant-filled-primary"
												><i class="fa-solid fa-download mr-2" /> {m.exportButton()}
											</a>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/each}
				</div>
			{:else if tabSet === 4}
				<div id="title" class="text-lg font-black">{m.composer()}</div>
				<select id="composer_select" hidden>
					{#each risk_assessments as risk_assessment}
						<option value={risk_assessment.id}>{risk_assessment.name}</option>
					{/each}
				</select>
				<div>
					{m.composerDescription()}:
					<ul class="list-disc px-4 py-2 mx-4 my-2">
						<li>
							{m.composerDescription1()}
						</li>
						<li>
							{m.composerDescription2()}
						</li>
					</ul>
				</div>

				<ComposerSelect composerForm={data.composerForm} />
			{/if}
		</div>
	</svelte:fragment>
</TabGroup>
