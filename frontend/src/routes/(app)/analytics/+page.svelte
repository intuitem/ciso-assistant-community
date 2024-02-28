<script lang="ts">
	import { MONTH_LIST } from '$lib/utils/constants';
	import type { SecurityMeasureSchema } from '$lib/utils/schemas';
	import type { AggregatedData, Counter, SecurityMeasureStatus, User } from '$lib/utils/types';
	import { beforeUpdate, onMount } from 'svelte';

	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import WatchlistExceptions from '$lib/components/fragments/WatchlistExceptions.svelte';
	import WatchlistMeasures from '$lib/components/fragments/WatchlistMeasures.svelte';
	import TreatmentProgressDualBar from '$lib/components/Chart/TreatmentProgressDualBar.svelte';

	import { RISK_COLOR_PALETTE } from '$lib/utils/constants';

	import * as m from '$paraglide/messages';
	import { localItems } from '$lib/utils/locales.js';
	import { languageTag } from '$paraglide/runtime';

	export let data;

	let user: User = data.user;
	let security_measure_status: SecurityMeasureStatus = data.security_measure_status;
	let measures = data.measures;
	let counters: Counter = data.get_counters;

	let risk_level = data.risks_level;
	let measures_to_review = data.measures_to_review;
	let acceptances_to_review = data.acceptances_to_review;
	let agg_data: AggregatedData = data.agg_data;
	let risk_assessments = data.risk_assessments;

	let viewable_measures: (typeof SecurityMeasureSchema)[] = data.viewable_measures;
	let updatable_measures: (typeof SecurityMeasureSchema)[] = data.updatable_measures;

	let openTab = 1;

	const cur_rsk_label = m.currentRisk();
	const rsd_rsk_label = m.residualRisk();

	let dropdown_selected_values: any;

	for (const item in security_measure_status.labels) {
		security_measure_status.labels[item] = localItems(languageTag())[
			security_measure_status.localLables[item]
		];
	}

	onMount(async () => {
		const echarts = await import('echarts');
		let echart_element = document.getElementById('security_measures_status_div');

		let security_measures_status_div_ch = echarts.init(echart_element, null, { renderer: 'svg' });

		let option = {
			xAxis: {
				type: 'category',
				data: security_measure_status.labels
			},
			yAxis: {
				type: 'value',
				allowDecimals: false,
				minInterval: 1
			},
			series: [
				{
					data: security_measure_status.values,
					type: 'bar'
				}
			]
		};

		security_measures_status_div_ch.setOption(option);

		let echart_resize_handler = () => {
			security_measures_status_div_ch.resize();
		};

		window.addEventListener('resize', echart_resize_handler); // Why this event listener can't be cleared by onDestroy ?

		dropdown.loadOptions(document);
	});

	beforeUpdate(() => {
		dropdown_selected_values = dropdown.selectedValues(document);
	});

	function setOpenTab(_openTab: number) {
		openTab = _openTab;
	}

	function get_measure_style(security_measure: SecurityMeasureSchema): string {
		if (security_measure.status === 'open') {
			return 'bg-blue-300 text-black';
		}
		if (security_measure.status === 'in_progress') {
			return 'bg-orange-300 text-black';
		}
		if (security_measure.status === 'on_hold') {
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

<div class="h-screen w-auto">
	<div class="px-4 flex flex-row mb-0">
		<button
			class="space-x-1 flex flex-row cursor-pointer px-4 py-1 w-fit border-slate-300 hover:bg-gray-100 rounded-t-lg hover:border-slate-400 text-center {openTab !==
			1
				? 'border-b'
				: 'bg-white border-b-0'}"
			on:click={() => setOpenTab(1)}
		>
			<span class="">
				<i class="fas fa-chart-pie" />
			</span>
			<div class="w-full">{m.summary()}</div>
		</button>
		<button
			class="space-x-1 flex flex-row cursor-pointer px-4 py-1 w-fit border-slate-300 hover:bg-gray-100 rounded-t-lg hover:border-slate-400 text-center {openTab !==
			2
				? 'border-b'
				: 'bg-white border-b-0'}"
			on:click={() => setOpenTab(2)}
		>
			<span class="">
				<i class="fas fa-star" />
			</span>
			<div class="w-full">{m.compliance()}</div>
		</button>
		<button
			class="space-x-1 flex flex-row cursor-pointer px-4 py-1 w-fit border-slate-300 hover:bg-gray-100 rounded-t-lg hover:border-slate-400 text-center {openTab !==
			3
				? 'border-b'
				: 'bg-white border-b-0'}"
			on:click={() => setOpenTab(3)}
		>
			<span class="">
				<i class="fas fa-heartbeat" />
			</span>
			<div class="w-full">{m.treatment()}</div>
		</button>
		<button
			class="space-x-1 flex flex-row cursor-pointer px-4 py-1 w-fit border-slate-300 hover:bg-gray-100 rounded-t-lg hover:border-slate-400 text-center {openTab !==
			4
				? 'border-b'
				: 'bg-white border-b-0'}"
			on:click={() => setOpenTab(4)}
		>
			<span class="">
				<i class="fas fa-drafting-compass" />
			</span>
			<div class="w-full">{m.composer()}</div>
		</button>
	</div>

	<div class:hide={openTab !== 1}>
		<section class="p-2 bg-white rounded-lg shadow-lg mb-6" id="stats">
			<div class="p-2 m-2">
				<span class="text-2xl font-extrabold text-slate-700">{m.statistics()}</span>
			</div>
			<div class="flex items-center content-center">
				<div class="w-1/4 p-2 m-2 flex content-center bg-white">
					<div class="text-5xl text-blue-500 mr-2"><i class="fas fa-glasses" /></div>
					<div class=" text-left">
						<div class="text-4xl font-bold">{counters.RiskAssessment}</div>
						<div class="font-semibold text-slate-500 text-sm">{m.riskAssessments()}</div>
					</div>
				</div>
				<div class="w-1/4 p-2 m-2 flex content-center bg-white">
					<div class="text-5xl text-yellow-500 mr-2"><i class="fas fa-clone" /></div>
					<div class=" text-left">
						<div class="text-4xl font-bold">{counters.RiskScenario}</div>
						<div class="font-semibold text-slate-500 text-sm">{m.scenarios()}</div>
					</div>
				</div>
				<div class="w-1/4 p-2 m-2 flex content-center bg-white">
					<div class="text-5xl text-red-500 mr-2"><i class="fas fa-fire-extinguisher" /></div>
					<div class=" text-left">
						<div class="text-4xl font-bold">{counters.SecurityMeasure}</div>
						<div class="font-semibold text-slate-500 text-sm">{m.securityMeasures()}</div>
					</div>
				</div>
				<div class="w-1/4 p-2 m-2 flex content-center bg-white">
					<div class="text-5xl text-green-500 mr-2"><i class="fas fa-user-tie" /></div>
					<div class=" text-left">
						<div class="text-4xl font-bold">{counters.RiskAcceptance}</div>
						<div class="font-semibold text-slate-500 text-sm">{m.riskAcceptances()}</div>
					</div>
				</div>
			</div>
		</section>

		<section class="p-2 bg-white rounded-lg shadow-lg mb-6" id="">
			<div class="p-2 m-2">
				<div class="text-2xl font-extrabold text-slate-700">{m.myProjects()}</div>
				<div class="text-sm text-slate-500 font-semibold">
					{#if counters.Project > 1}
						{m.assignedProjects({ number: counters.Project, s: 's' })}
					{:else}
						{m.assignedProjects({ number: counters.Project, s: '' })}
					{/if}
				</div>
			</div>
			<div class="flex items-center content-center">
				<div class="h-96 p-2 m-2 w-1/3">
					<span class="text-sm font-semibold">{m.currentRiskLevelPerScenario()}</span>

					<DonutChart
						name="current_risk"
						s_label={cur_rsk_label}
						values={risk_level.current}
						colors={risk_level.current.map(object => object.color)}
					/>
				</div>
				<div class="h-96 p-2 m-2 w-1/3">
					<span class="text-sm font-semibold">{m.residualRiskLevelPerScenario()}</span>

					<DonutChart
					name="residual_risk"
						s_label={rsd_rsk_label}
						values={risk_level.residual}
						colors={risk_level.residual.map(object => object.color)}
					/>
				</div>
				<div class="h-96 p-2 m-2 w-1/3">
					<span class="text-sm font-semibold">{m.securityMeasuresStatus()}</span>

					<!-- -----------MEASURE STATUS------------ -->

					<div id="security_measures_status_div" class="bg-white w-auto h-full" />

					<!-- -----------MEASURE STATUS------------ -->
				</div>
			</div>
		</section>

		<section class="p-2 bg-white rounded-lg shadow-lg mb-6" id="">
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
	</div>
	<div class:hide={openTab !== 4}>
		<main class="p-2 bg-white rounded-lg shadow-lg mb-6">
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
								on:click|stopPropagation={handle_composer_submit_click}>{m.processButton()}</button
							>
							<div class="flex flex-col items-center relative">
								<button
									on:click|stopPropagation={() => dropdown.open(dropdown)}
									class="w-full svelte-1l8159u cursor-pointer"
								>
									<div class="my-2 p-1 flex border border-gray-200 bg-white rounded svelte-1l8159u">
										<div class="flex flex-auto flex-wrap">
											{#each dropdown.selected as option, index (dropdown.options[option].value)}
												<div
													class="flex justify-center items-center m-1 font-medium py-1 px-2 rounded-full text-indigo-700 bg-indigo-100 border border-indigo-300"
												>
													<div class="text-xs font-normal leading-none max-w-full flex-initial">
														{dropdown.options[option].text}
													</div>
													<div class="flex flex-auto flex-row-reverse">
														<button on:click|stopPropagation={() => dropdown.remove(index, option)}>
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
																	<!-- x-text="option.text" -->
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
		</main>
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
										<th class="text-left py-2 px-4">{m.securityMeasure()}</th>
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
												<td class="text-center py-2 px-4 {get_measure_style(mtg)}">{localItems(languageTag())[mtg.status]}</td>
												<td class="text-center py-2 px-4"
													>{#if mtg.meta} {formatDate(mtg.meta)} {:else} -- {/if}</td
												>
												<td class="text-center py-2 px-4">
													{#if mtg.id in viewable_measures}
														<a
															href="/security-measures/{mtg.id}"
															class="text-indigo-500 hover:text-indigo-300"
															><i class="fas fa-eye" /></a
														>
													{/if}
													{#if mtg.id in updatable_measures}
														<a
															href="/security-measures/{mtg.id}/edit"
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
													{m.noPendingSecurityMeasure()}.
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
	{#if openTab === 2}
		<div class="h-full">
			<main class="p-2 bg-white rounded-lg shadow-lg mb-6">
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
											colors={compliance_assessment.donut.values.map(object => object.itemStyle.color)}
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
			</main>
		</div>
		<div class="p-2 m-2" />
	{/if}
</div>

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
