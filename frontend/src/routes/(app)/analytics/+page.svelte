<script lang="ts">
	import { MONTH_LIST } from '$lib/utils/constants';
	import type { AppliedControlSchema } from '$lib/utils/schemas';
	import type { AggregatedData, Counter, AppliedControlStatus, User } from '$lib/utils/types';
	import { beforeUpdate, onMount } from 'svelte';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import WatchlistExceptions from '$lib/components/fragments/WatchlistExceptions.svelte';
	import WatchlistMeasures from '$lib/components/fragments/WatchlistMeasures.svelte';
	import TreatmentProgressDualBar from '$lib/components/Chart/TreatmentProgressDualBar.svelte';

	import { RISK_COLOR_PALETTE } from '$lib/utils/constants';

	import * as m from '$paraglide/messages';
	import { localItems } from '$lib/utils/locales.js';
	import { languageTag } from '$paraglide/runtime';
	import { Tab, TabGroup } from '@skeletonlabs/skeleton';
	import CounterCard from './CounterCard.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';

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
	let applied_control_status: AppliedControlStatus = data.applied_control_status;
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

	for (const item in applied_control_status.labels) {
		applied_control_status.labels[item] = localItems(languageTag())[
			applied_control_status.localLables[item]
		];
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

	let dropdown = new Dropdown();

	let tabSet = 0;
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
	<Tab bind:group={tabSet} name="governance" value={0}>Governance</Tab>
	<Tab bind:group={tabSet} name="risk" value={1}>Risk</Tab>
	<Tab bind:group={tabSet} name="compliance" value={2}>Compliance</Tab>
	<Tab bind:group={tabSet} name="composer" value={3}>Composer</Tab>
	<svelte:fragment slot="panel">
		<div class="px-4">
			{#if tabSet === 0}
				<section id="stats">
					<span class="text-xl font-extrabold">{m.statistics()}</span>
					<div class="flex justify-between">
						<CounterCard
							count={counters.domains}
							label={m.domains()}
							faIcon="fa-solid fa-diagram-project"
						/>
						<CounterCard
							count={counters.projects}
							label={m.projects()}
							faIcon="fa-solid fa-cubes"
						/>
						<CounterCard
							count={counters.applied_controls}
							label={m.appliedControls()}
							faIcon="fa-solid fa-fire-extinguisher"
						/>
						<CounterCard
							count={counters.risk_assessments}
							label={m.riskAssessments()}
							faIcon="fa-solid fa-magnifying-glass-chart"
						/>
						<CounterCard
							count={counters.compliance_assessments}
							label={m.complianceAssessments()}
							faIcon="fa-solid fa-arrows-to-eye"
						/>
						<CounterCard count={counters.policies} label={m.policies()} faIcon="fas fa-file-alt" />
					</div>
				</section>
				<section>
					<div class="flex flex-row [&>*]:w-1/2">
						<div class="h-96">
							<BarChart
								name="mtg"
								title={m.appliedControlsStatus()}
								labels={applied_control_status.labels}
								values={applied_control_status.values}
							/>
						</div>
						<div class="flex flex-col space-y-4 h-96 text-sm whitespace-nowrap">
							<BarChart
								horizontal
								name="usedMatrices"
								title={m.usedRiskMatrices()}
								labels={data.usedRiskMatrices.map((matrix) => matrix.name)}
								values={data.usedRiskMatrices.map((matrix) => matrix.risk_assessments_count)}
							/>
							<BarChart
								horizontal
								name="usedFrameworks"
								title={m.usedFrameworks()}
								labels={data.usedFrameworks.map((framework) => framework.name)}
								values={data.usedFrameworks.map(
									(framework) => framework.compliance_assessments_count
								)}
							/>
						</div>
					</div>
				</section>
				<section>
					<div class="p-2 m-2">
						<div class="text-2xl font-extrabold text-slate-700">{m.watchlist()}</div>
						<div class="text-sm text-slate-500 font-semibold">
							{m.watchlistDescription()}
						</div>
					</div>
					<div class="p-2 m-2 flex flex-col space-y-5 items-center content-center">
						<div class="w-full">
							<span class="text-md font-semibold">{m.measuresToReview()}</span>

							<WatchlistMeasures {measures_to_review} />
						</div>
						<div class="w-full">
							<span class="text-md font-semibold">{m.exceptionsToReview()}</span>

							<WatchlistExceptions {acceptances_to_review} {user} />
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
									<div class="card w-full bg-white flex flex-row shadow mx-8 p-4 relative">
										<div class="w-1/5 flex flex-col space-y-2">
											<div>
												<p class="font-medium">{m.name()}</p>
												<p>{compliance_assessment.name}</p>
											</div>
											<div>
												<p class="font-medium">{m.framework()}</p>
												<p>{compliance_assessment.framework.str}</p>
											</div>
										</div>
										<div class="w-3/5 h-32">
											<DonutChart
												name="compliance_assessments"
												s_label={m.complianceAssessments()}
												values={compliance_assessment.donut.values}
												colors={compliance_assessment.donut.values.map(
													(object) => object.itemStyle.color
												)}
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

					<div class="w-full flex flex-col items-center h-auto mx-auto">
						<form
							action="/analytics/composer/"
							class="bg-gray-50 m-2 p-4 rounded-lg shadow-lg"
							id="composer_form"
							on:submit={handle_composer_submit}
						>
							<input name="risk_assessment" type="hidden" value={dropdown_selected_values} />

							<div class="inline-block relative w-96">
								<button
									id="process"
									class="text-md text-white p-2 rounded w-full"
									on:click|stopPropagation={handle_composer_submit_click}
									>{m.processButton()}</button
								>
								<div class="flex flex-col items-center relative">
									<button
										on:click|stopPropagation={() => dropdown.open(dropdown)}
										class="w-full svelte-1l8159u cursor-pointer"
									>
										<div
											class="my-2 p-1 flex border border-gray-200 bg-white rounded svelte-1l8159u"
										>
											<div class="flex flex-auto flex-wrap">
												{#each dropdown.selected as option, index (dropdown.options[option].value)}
													<div
														class="flex justify-center items-center m-1 font-medium py-1 px-2 rounded-full text-indigo-700 bg-indigo-100 border border-indigo-300"
													>
														<div class="text-xs font-normal leading-none max-w-full flex-initial">
															{dropdown.options[option].text}
														</div>
														<div class="flex flex-auto flex-row-reverse">
															<button
																on:click|stopPropagation={() => dropdown.remove(index, option)}
															>
																<svg class="fill-current h-6 w-6" role="button" viewBox="0 0 20 20">
																	<path
																		d="M14.348,14.849c-0.469,0.469-1.229,0.469-1.697,0L10,11.819l-2.651,3.029c-0.469,0.469-1.229,0.469-1.697,0
                                    c-0.469-0.469-0.469-1.229,0-1.697l2.758-3.15L5.651,6.849c-0.469-0.469-0.469-1.228,0-1.697s1.228-0.469,1.697,0L10,8.183
                                    l2.651-3.031c0.469-0.469,1.228-0.469,1.697,0s0.469,1.229,0,1.697l-2.758,3.152l2.758,3.15
                                    C14.817,13.62,14.817,14.38,14.348,14.849z"
																	/>
																</svg>
															</button>
														</div>
													</div>
												{/each}
												<div class:hide={dropdown.selected.length !== 0} class="flex">
													<input
														placeholder={m.selectTargets()}
														class="input bg-transparent text-gray-800 cursor-pointer select-none ring-0 border-0 outline-0"
													/>
												</div>
											</div>
											<div
												class="text-gray-300 w-8 border-l flex items-center border-gray-200 svelte-1l8159u"
											>
												<button
													id="closemenu"
													type="button"
													on:click|stopPropagation={() => dropdown.open(dropdown)}
													class="cursor-pointer w-6 h-6 text-gray-600 outline-none focus:outline-none {dropdown.show
														? 'hide'
														: ''}"
												>
													<svg version="1.1" class="fill-current h-4 w-4" viewBox="0 0 20 20">
														<path
															d="M17.418,6.109c0.272-0.268,0.709-0.268,0.979,0s0.271,0.701,0,0.969l-7.908,7.83
c-0.27,0.268-0.707,0.268-0.979,0l-7.908-7.83c-0.27-0.268-0.27-0.701,0-0.969c0.271-0.268,0.709-0.268,0.979,0L10,13.25
L17.418,6.109z"
														/>
													</svg>
												</button>
												<button
													id="openmenu"
													type="button"
													on:click|stopPropagation={() => dropdown.close(dropdown)}
													class="cursor-pointer w-6 h-6 text-gray-600 outline-none focus:outline-none {!dropdown.show
														? 'hide'
														: ''}"
												>
													<svg class="fill-current h-4 w-4" viewBox="0 0 20 20">
														<path
															d="M2.582,13.891c-0.272,0.268-0.709,0.268-0.979,0s-0.271-0.701,0-0.969l7.908-7.83
c0.27-0.268,0.707-0.268,0.979,0l7.908,7.83c0.27,0.268,0.27,0.701,0,0.969c-0.271,0.268-0.709,0.268-0.978,0L10,6.75L2.582,13.891z
"
														/>
													</svg>
												</button>
											</div>
										</div>
									</button>
									<div class="w-full px-4">
										<button
											class="absolute shadow top-100 bg-white z-40 w-full lef-0 rounded max-h-select overflow-y-auto svelte-5uyqqj"
											on:click|stopPropagation={() => dropdown.close(dropdown)}
										>
											<div class="flex flex-col w-full">
												{#if dropdown.show}
													{#each dropdown.options as option, index (option)}
														<div>
															<button
																class="cursor-pointer w-full border-gray-100 rounded-t border-b hover:bg-indigo-100"
																on:click|stopPropagation={(event) => dropdown.select(index, event)}
															>
																<div
																	id="option"
																	class:border-indigo-600={option.selected}
																	class="flex w-full items-center p-2 pl-2 border-transparent border-l-2 relative"
																>
																	<div class="w-full items-center flex">
																		<div class="mx-2 leading-6" x-model="option">{option.text}</div>
																	</div>
																</div>
															</button>
														</div>
													{/each}
												{/if}
											</div>
										</button>
									</div>
								</div>
							</div>
						</form>
					</div>
				</div>
			{/if}
		</div>
	</svelte:fragment>
</TabGroup>

<div class:hide={openTab !== 4}>
	<main class="p-2 bg-white rounded-lg shadow-lg mb-6" />
</div>
{#if openTab === 3}
	<div class="h-full">
		<main class="p-2 bg-white rounded-lg shadow-lg mb-6">
			<div class="">
				{#if agg_data.names.length}
					<div class="m-2 p-2">
						<div>
							<div>{m.treatmentProgressOverview()}</div>
							<div class="rounded items-center justify-center">
								<TreatmentProgressDualBar {agg_data} />
							</div>
						</div>
					</div>
					<div class="p-4 m-2">
						<div class="text-lg font-semibold">{m.pendingMeasures()}</div>
						<div class="text-sm pb-4">{m.orderdByRankingScore()}</div>
						<div class="flex items-center justify-center">
							<table class="p-2 m-2 w-full">
								<tr class="bg-gray-100">
									<th class="text-left py-2 px-4">{m.domain()}</th>
									<th class="text-left py-2 px-4">{m.appliedControl()}</th>
									<th>{m.rankingScore()}</th>
									<th>{m.status()}</th>
									<th>{m.eta()}</th>
									<th class="py-2 px-4">{m.actions()}</th>
								</tr>

								{#if measures.length > 0}
									{#each measures as mtg}
										<tr class="border-b">
											<td class="text-left py-2 px-4">{mtg.folder.str}</td>
											<td class="text-left py-2 px-4">{mtg.name}</td>
											<td class="text-center py-2 px-4">{mtg.ranking_score}</td>
											<td class="text-center py-2 px-4 {get_measure_style(mtg)}"
												>{localItems(languageTag())[mtg.status]}</td
											>
											<td class="text-center py-2 px-4"
												>{#if mtg.meta} {formatDate(mtg.meta)} {:else} -- {/if}</td
											>
											<td class="text-center py-2 px-4">
												{#if mtg.id in viewable_measures}
													<a
														href="/applied-controls/{mtg.id}"
														class="text-indigo-500 hover:text-indigo-300"
														><i class="fas fa-eye" /></a
													>
												{/if}
												{#if mtg.id in updatable_measures}
													<a
														href="/applied-controls/{mtg.id}/edit"
														class="text-indigo-500 hover:text-indigo-300"
														><i class="fas fa-pen-square" /></a
													>
												{/if}
											</td>
										</tr>{/each}
								{:else}
									<tr class="text-black p-4 text-center">
										<td colspan="8" class="py-2">
											<i class="inline fas fa-exclamation-triangle" />
											<p class="inline test-gray-900">
												{m.noPendingAppliedControl()}.
											</p>
										</td>
									</tr>
								{/if}
							</table>
						</div>
						<div class="text-sm p-2 m-2">
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
		</main>
	</div>
	<div class="p-2 m-2" />
{/if}

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
