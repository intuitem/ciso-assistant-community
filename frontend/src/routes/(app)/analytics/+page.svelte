<script lang="ts">
	import { MONTH_LIST } from '$lib/utils/constants';
	import type { AppliedControlSchema } from '$lib/utils/schemas';
	import type { AggregatedData, Counter, AppliedControlStatus, User } from '$lib/utils/types';
	import { beforeUpdate, onMount } from 'svelte';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';

	import * as m from '$paraglide/messages';
	import { localItems } from '$lib/utils/locales.js';
	import { languageTag } from '$paraglide/runtime';
	import { Tab, TabGroup, tableSourceMapper } from '@skeletonlabs/skeleton';
	import CounterCard from './CounterCard.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import ComposerSelect from './ComposerSelect.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';

	interface Counters {
		domains: number;
		projects: number;
		applied_controls: number;
		risk_assessments: number;
		compliance_assessments: number;
		policies: number;
	}

	export let data;

	let user: User = data.user;
	let measures = data.measures;
	let counters: Counters = data.get_counters;

	let risk_level = data.risks_level;
	let measures_to_review = data.measures_to_review;
	let acceptances_to_review = data.acceptances_to_review;
	let agg_data: AggregatedData = data.agg_data;
	let risk_assessments = data.risk_assessments;

	let viewable_measures: (typeof AppliedControlSchema)[] = data.viewable_measures;
	let updatable_measures: (typeof AppliedControlSchema)[] = data.updatable_measures;

	let openTab = 0;

	const cur_rsk_label = m.currentRisk();
	const rsd_rsk_label = m.residualRisk();

	let dropdown_selected_values: any;

	function localizeChartLabels(labels: string[]): string[] {
		return labels.map((label) => localItems(languageTag())[label]);
	}

	onMount(async () => {
		dropdown.loadOptions(document);
	});

	beforeUpdate(() => {
		dropdown_selected_values = dropdown.selectedValues(document);
	});

	function get_measure_style(applied_control: AppliedControlSchema): string {
		if (applied_control.status === 'open') {
			return 'bg-blue-300 text-black';
		}
		if (applied_control.status === 'in_progress') {
			return 'bg-orange-300 text-black';
		}
		if (applied_control.status === 'on_hold') {
			return 'bg-red-400 text-black';
		}
		return '';
	}

	function formatDate(date: Date): string {
		// Is this the best date format ?
		return `${MONTH_LIST[date.getMonth() - 1]} ${date.getDay()}, ${date.getFullYear()}`;
	}

	function handle_composer_submit(event: Event) {
		event.preventDefault();
	}

	function handle_composer_submit_click(event) {
		let form = document.getElementById('composer_form');
		form.submit();
	}

	function dropdown_react() {
		dropdown = dropdown;
	}

	class Dropdown {
		options: any[]; // Change this type later on
		selected: any[]; // Change this type later on
		show: boolean;

		constructor() {
			this.options = [];
			this.selected = [];
			this.show = false;
		}

		open(_this: Dropdown) {
			this.show = true;
			dropdown_react();
		}
		close(_this: Dropdown) {
			_this.show = false;
			dropdown_react();
		}

		select(index: number, event) {
			if (!this.options[index].selected) {
				this.options[index].selected = true;
				this.options[index].element = event.target;
				this.selected.push(index);
			} else {
				this.selected.splice(this.selected.lastIndexOf(index), 1);
				this.options[index].selected = false;
			}
			dropdown_react();
		}
		remove(index: number, option) {
			this.options[option].selected = false;
			this.selected.splice(index, 1);
			dropdown_react();
		}
		loadOptions(document: Document) {
			const options = document.getElementById('composer_select')?.options;
			for (let i = 0; i < options.length; i++) {
				this.options.push({
					value: options[i].value,
					text: options[i].innerText,
					selected:
						options[i].getAttribute('selected') != null
							? options[i].getAttribute('selected')
							: false
				});
			}
		}
		selectedValues(document: Document) {
			const submitButton = document.getElementById('process');
			if (!submitButton) {
				return; // Handle the null scenario
			}
			if (this.selected.length == 0) {
				submitButton.disabled = true;
				submitButton.classList.remove('bg-violet-800', 'hover:bg-violet-700');
				submitButton.classList.add('bg-gray-300', 'text-gray-200');
			} else {
				submitButton.disabled = false;
				submitButton.classList.add('bg-violet-800', 'hover:bg-violet-700');
			}
			return this.selected.map((option) => {
				return this.options[option].value;
			});
		}
	}

	const appliedControlTodoTable: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			folder: 'domain',
			ranking_score: 'rankingScore',
			eta: 'eta'
		},
		body: tableSourceMapper(data.measures, ['name', 'category', 'folder', 'ranking_score', 'eta']),
		meta: data.measures
	};

	const appliedControlWatchlistTable: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			folder: 'domain',
			eta: 'eta',
			expiry_date: 'expiryDate'
		},
		body: tableSourceMapper(data.measures_to_review, [
			'name',
			'category',
			'folder',
			'eta',
			'expiry_date'
		])
	};

	const riskAcceptanceWatchlistTable: TableSource = {
		head: {
			name: 'name',
			risk_scenarios: 'riskScenarios',
			expiry_date: 'expiryDate'
		},
		body: tableSourceMapper(data.acceptances_to_review, ['name', 'risk_scenarios', 'expiry_date'])
	};

	let dropdown = new Dropdown();

	let tabSet = $page.url.searchParams.get('tab') ? parseInt($page.url.searchParams.get('tab')) : 0;
	$: if (browser) {
		$page.url.searchParams.set('tab', tabSet.toString());
		goto($page.url);
	}
</script>

<svelte:head>
	<title>{m.analytics()}</title>
</svelte:head>

<svelte:document
	on:click={() => {
		if (openTab === 3 && dropdown.show) {
			dropdown.close(dropdown);
		}
	}}
/>

<TabGroup>
	<Tab bind:group={tabSet} name="governance" value={0}>{m.governance()}</Tab>
	<Tab bind:group={tabSet} name="risk" value={1}>{m.risk()}</Tab>
	<Tab bind:group={tabSet} name="compliance" value={2}>{m.compliance()}</Tab>
	<Tab bind:group={tabSet} name="composer" value={3}>{m.composer()}</Tab>
	<svelte:fragment slot="panel">
		<div class="px-4 space-y-4">
			{#if tabSet === 0}
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
				<section>
					<div class="flex flex-row space-x-4 h-96 text-sm whitespace-nowrap [&>*]:w-full">
						<BarChart
							name="usedMatrices"
							title={m.usedRiskMatrices()}
							labels={data.usedRiskMatrices.map((matrix) => matrix.name)}
							values={data.usedRiskMatrices.map((matrix) => matrix.risk_assessments_count)}
						/>
						<BarChart
							name="usedFrameworks"
							title={m.usedFrameworks()}
							labels={data.usedFrameworks.map((framework) => framework.name)}
							values={data.usedFrameworks.map(
								(framework) => framework.compliance_assessments_count
							)}
						/>
						<BarChart
							name="riskAssessmentsPerStatus"
							title={m.riskAssessmentsStatus()}
							labels={localizeChartLabels(data.riskAssessmentsPerStatus.localLables)}
							values={data.riskAssessmentsPerStatus.values}
						/>
						<BarChart
							name="complianceAssessmentsPerStatus"
							title={m.complianceAssessmentsStatus()}
							labels={localizeChartLabels(data.complianceAssessmentsPerStatus.localLables)}
							values={data.complianceAssessmentsPerStatus.values}
						/>
					</div>
					<div>
						{#if agg_data.names.length}
							<div class="m-2 p-2" />
							<div>
								<div class="text-xl font-extrabold">{m.pendingMeasures()}</div>
								<div class="text-sm text-gray-500">
									{m.orderdByRankingScore()}
								</div>
								<ModelTable
									URLModel="applied-controls"
									source={appliedControlTodoTable}
									search={false}
									pagination={false}
								/>
								<div class="text-sm">
									<i class="fas fa-info-circle" />
									{m.rankingScoreDefintion()}.
								</div>
							</div>
						{:else}
							<div class="bg-white shadow-md rounded-lg px-4 py-2 m-8">
								<div>{m.projectsSummaryEmpty()}.</div>
							</div>
						{/if}
					</div>
				</section>
				<section>
					<div>
						<div class="text-xl font-extrabold">{m.watchlist()}</div>
						<div class="text-sm text-gray-500">
							{m.watchlistDescription()}
						</div>
					</div>
					<div class="flex flex-col space-y-5 items-center content-center">
						<div class="w-full">
							<span class="text-md font-semibold">{m.measuresToReview()}</span>
							<ModelTable source={appliedControlWatchlistTable} search={false} pagination={false} />
						</div>
						<div class="w-full">
							<span class="text-md font-semibold">{m.exceptionsToReview()}</span>
							<ModelTable source={riskAcceptanceWatchlistTable} search={false} pagination={false} />
						</div>
					</div>
				</section>
			{:else if tabSet === 1}
				<section>
					<div class="flex">
						<div class="h-96 flex-1">
							<span class="text-sm font-semibold">{m.currentRiskLevelPerScenario()}</span>

							<DonutChart
								name="current_risk"
								s_label={cur_rsk_label}
								values={risk_level.current}
								colors={risk_level.current.map((object) => object.color)}
							/>
						</div>
						<div class="h-96 flex-1">
							<span class="text-sm font-semibold">{m.residualRiskLevelPerScenario()}</span>

							<DonutChart
								name="residual_risk"
								s_label={rsd_rsk_label}
								values={risk_level.residual}
								colors={risk_level.residual.map((object) => object.color)}
							/>
						</div>
					</div>
					<div class="h-96">
						<BarChart
							name="mtg"
							title={m.appliedControlsStatus()}
							labels={localizeChartLabels(data.applied_control_status.localLables)}
							values={data.applied_control_status.values}
						/>
					</div>
				</section>
			{:else if tabSet === 2}
				<div class="h-full">
					<span class="text-2xl font-extrabold">{m.overallCompliance()}</span>
					<div class="flex flex-col space-y-2">
						{#each data.projects as project}
							<div class="flex flex-col items-center">
								{#if project.compliance_assessments && project.compliance_assessments.length > 1}
									<div class="flex flex-row space-x-2 w-1/2 justify-between items-center">
										<span class="text-xl font-semibold">{project.name}</span>
										<div class="flex flex-1 bg-gray-200 rounded-full overflow-hidden h-4 shrink">
											{#each project.overallCompliance.values as sp}
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
												<p>{compliance_assessment.name}</p>
											</div>
											<div>
												<p class="text-sm font-semibold">{m.framework()}</p>
												<p>{compliance_assessment.framework.str}</p>
											</div>
										</div>
										<div class="w-3/5 h-32">
											<DonutChart
												name="compliance_assessments"
												s_label={m.complianceAssessments()}
												values={compliance_assessment.donut.values}
											/>
										</div>
										<div class="absolute top-0 right-0 mt-2 space-x-1">
											<a
												href="/compliance-assessments/{compliance_assessment.id}/export"
												class="btn variant-filled-primary"
												><i class="fa-solid fa-download mr-2" /> {m.exportButton()}
											</a>
											<a
												href="/compliance-assessments/{compliance_assessment.id}/edit"
												class="btn variant-filled-primary"
												><i class="fa-solid fa-edit mr-2" /> {m.edit()}
											</a>
										</div>
									</div>
								{/each}
							</div>
						{/each}
					</div>
				</div>
				<div class="p-2 m-2" />
			{:else if tabSet === 3}
				<div class="p-2 m-2">
					<div id="title" class="text-lg font-black m-1 p-1">{m.composer()}</div>
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
				</div>
			{/if}
		</div>
	</svelte:fragment>
</TabGroup>

<style>
	.hide {
		display: none;
	}
	:is(#openmenu, #closemenu) {
		width: 100%;
		height: 100%;
		padding: 4px 4px 4px 8px; /* py-1 pl-2 pr-1 */
		box-sizing: border-box;
	}
</style>
