<script lang="ts">
	import type { RiskMatrixJsonDefinition } from '$lib/utils/types';
	import Selector from './selector.svelte';
	import { average, forms } from './utils';
	import * as m from '$paraglide/messages';

	export let data;
	export let risk_matrices = data.risk_matrices;

	let risk_matrix_select: Element;
	let risk_matrix: RiskMatrixJsonDefinition;
	let is_business_impact_ignored = false;

	let risk_matrix_index = 0;
	$: risk_matrix = risk_matrices[risk_matrix_index] ?? null;

	let vector: number[];
	let vector_string: string;
	let form_data = {
		threat_agent: [0, 0, 0, 0],
		business_impact: [0, 0, 0, 0],
		vulnerability: [0, 0, 0, 0],
		technical_impact: [0, 0, 0, 0]
	};

	$: threat_agent_score = average(form_data.threat_agent);
	$: business_impact_score = average(form_data.business_impact);
	$: vulnerability_score = average(form_data.vulnerability);
	$: technical_impact_score = average(form_data.technical_impact);

	$: impact_score = is_business_impact_ignored ? technical_impact_score : business_impact_score;
	$: probability_score = average([threat_agent_score, vulnerability_score]);
	$: risk_score = average([impact_score, probability_score]);

	$: vector = [
		...form_data.threat_agent,
		...form_data.business_impact,
		...form_data.vulnerability,
		...form_data.technical_impact
	];

	$: {
		let strings: string[] = [];
		for (let i = 0; i < 4; i++) {
			strings.push(vector.slice(4 * i, 4 * (i + 1)).join(''));
		}
		vector_string = strings.join('-');
	}

	function update_scores(risk_score: number, risk_matrix: RiskMatrixJsonDefinition) {
		if (!risk_matrix) return;
		const probabilityPartitionSize = 10 / risk_matrix['probability'].length;
		const impactPartitionSize = 10 / risk_matrix['impact'].length;
		const riskPartitionSize = 10 / risk_matrix['risk'].length;

		const probability_index = Math.floor(probability_score / probabilityPartitionSize);
		const impact_index = Math.floor(impact_score / impactPartitionSize);
		const risk_index = Math.floor(risk_score / riskPartitionSize);

		return {
			probability: risk_matrix.probability[probability_index],
			impact: risk_matrix.impact[impact_index],
			risk: risk_matrix.risk[risk_index]
		};
	}

	$: labels = update_scores(risk_score, risk_matrix);
</script>

<main class="text-sm h-full flex flex-col">
	{#if risk_matrix}
		<div class="mx-auto">
			<div class="flex flex-col">
				<p class="text-sm">{m.riskMatrix()}</p>
				<select
					class="select form-input w-fit pr-8"
					bind:value={risk_matrix_index}
					bind:this={risk_matrix_select}
				>
					{#each risk_matrices as risk_matrix, index}
						<option value={index}>{risk_matrix.name}</option>
					{/each}
				</select>
			</div>
			<div class="grid lg:grid-cols-2">
				<div class="">
					<!--Threat Agent Factors-->
					<div
						id="ta_div"
						class="px-4 py-2 mx-1 my-2 bg-white shadow rounded h-1/2 grid grid-cols-5"
					>
						<div class="col-span-4 p-2">
							{#each forms.threat_agent as selector_data, index}
								<Selector
									{...selector_data}
									on:change={(e) => {
										form_data.threat_agent[index] = e.detail;
									}}
								/>
							{/each}
						</div>
						<div class="my-auto ml-2 col-span 1 w-full">
							<div class="shadow-lg bg-indigo-700 px-2 py-4 rounded-xl">
								<div class="text-gray-100 text-xs">{m.threatAgentFactors()}</div>
								<div class="font-bold text-white text-lg" id="threat_agent_score">
									{threat_agent_score}
								</div>
							</div>
						</div>
					</div>
					<!--Vulnerability Factors-->
					<div
						id="vf_div"
						class="px-4 py-2 mx-1 my-2 bg-white shadow rounded h-1/2 grid grid-cols-5"
					>
						<div class="col-span-4 p-2">
							{#each forms.vulnerability as selector_data, index}
								<Selector
									{...selector_data}
									on:change={(e) => {
										form_data.vulnerability[index] = e.detail;
									}}
								/>
							{/each}
						</div>
						<div class="my-auto ml-2 col-span 1 w-full">
							<div class="shadow-lg bg-indigo-700 px-2 py-4 rounded-xl">
								<div class="text-gray-100 text-xs">{m.vulnerabilityFactors()}</div>
								<div class="font-bold text-white text-lg" id="vulnerability_score">
									{vulnerability_score}
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="my-4 lg:my-0">
					<!--Business Impact Factors-->
					<div
						id="bi_div"
						class="px-4 py-2 mx-1 my-2 shadow rounded h-1/2 grid grid-cols-5 bg-white {is_business_impact_ignored
							? 'bg-gray-100 text-gray-400'
							: 'bg-white text-black'}"
					>
						<div class="col-span-4 p-2">
							{#each forms.business_impact as selector_data, index}
								<Selector
									{...selector_data}
									disabled={is_business_impact_ignored}
									on:change={(e) => {
										form_data.business_impact[index] = e.detail;
									}}
								/>
							{/each}
						</div>
						<div class="my-auto ml-2 col-span 1 w-full">
							<div class="shadow-lg bg-indigo-700 px-2 py-4 rounded-xl">
								<div class="text-gray-100 text-xs">{m.businessImpactFactors()}</div>
								<div class="font-bold text-white text-lg" id="business_impact_score">
									{is_business_impact_ignored ? '--' : business_impact_score}
								</div>
								<div class="flex flex-row space-x-2 items-center">
									<input
										id="ignore_business_impact"
										type="checkbox"
										class="w-4 h-4 bg-gray-100 border-gray-300 rounded
                focus:ring-2"
										bind:checked={is_business_impact_ignored}
									/>
									<label
										class="ml-2 text-sm font-medium text-gray-100"
										for="ignore_business_impact"
									>
										{m.ignore()}
									</label>
								</div>
							</div>
						</div>
					</div>
					<!--Technical Impact Factors-->
					<div
						id="ti_div"
						class="px-4 py-2 mx-1 my-2 bg-white shadow rounded h-1/2 grid grid-cols-5 {is_business_impact_ignored
							? 'bg-white text-black'
							: 'bg-gray-100 text-gray-400'}"
					>
						<div class="col-span-4 p-2">
							{#each forms.technical_impact as selector_data, index}
								<Selector
									{...selector_data}
									disabled={!is_business_impact_ignored}
									on:change={(e) => {
										form_data.technical_impact[index] = e.detail;
									}}
								/>
							{/each}
						</div>
						<div class="my-auto ml-2 col-span 1 w-full">
							<div class="shadow-lg bg-indigo-700 px-2 py-4 rounded-xl mx-auto">
								<div class="text-gray-100 text-xs">{m.technicalImpactFactors()}</div>
								<div class="font-bold text-white text-lg" id="technical_impact_score">
									{is_business_impact_ignored ? technical_impact_score : '--'}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="p-2 my-8 bg-white rounded shadow">
				<div class="p-1 m-1 text-xs">
					{m.assessmentVector()}: <span id="vector">{vector_string}</span>
				</div>
				<div class="grid grid-cols-3 grid-rows-1 items-center justify-center">
					<div class="mx-auto w-full">
						<div class="bg-cyan-600 p-4 m-2 rounded-lg shadow-lg lg:mx-4">
							<div class="text-gray-100 font-semibold">{m.probability()}</div>
							<div>
								<span class="text-xl text-white font-bold" id="probability_label"
									>{labels.probability.name}
									{probability_score === 0 ? '--' : probability_score}</span
								>
								<span class="text-white text-xs" id="probability_score" />
							</div>
						</div>
					</div>

					<div
						class="text-2xl p-2 grid grid-rows-2 grid-cols-3 items-center text-center w-full mb-4"
						id="score"
					>
						<div class="text-lg p-1 col-span-3">{m.riskLevel()}</div>
						<i class="fas fa-arrow-alt-circle-right" />
						<span
							class="py-2 px-0 font-semibold rounded shadow"
							id="risk_label"
							style="background-color: {labels.risk.hexcolor}"
						>
							<p class="overflow-clip">{labels.risk.name}</p></span
						>
						<i class="fas fa-arrow-alt-circle-left" />
					</div>

					<div class="mx-auto w-full">
						<div class="bg-cyan-600 p-4 m-2 rounded-lg shadow-lg lg:mx-4">
							<div class="text-gray-100 font-semibold">{m.impact()}</div>
							<div>
								<span class="text-xl text-white font-bold" id="impact_label"
									>{labels.impact.name} {impact_score === 0 ? '--' : impact_score}</span
								>
								<span class="text-white text-xs" id="impact_score" />
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	{:else}
		<div class="mx-auto w-full font-bold text-2xl text-center">
			{m.scoringAssistantNoMatrixError()}
		</div>
	{/if}
</main>
