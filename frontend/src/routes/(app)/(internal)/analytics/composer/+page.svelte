<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import { m } from '$paraglide/messages';
	import type { AppliedControlStatus } from '$lib/utils/types';

	
	interface Props {
		// Props
		data: any;
	}

	let { data }: Props = $props();

	// Make a reactive copy of data to track changes properly
	let riskData = $state({ ...data });
	riskData.risk_assessment_objects.forEach((risk_assessment: Record<string, any>) => {
		risk_assessment.show = false;
	});

	let applied_control_status: AppliedControlStatus = riskData.applied_control_status;
</script>

<div class="flex flex-col space-y-4 p-2">
	<div>
		<div class="px-2 mx-2 font-semibold text-xl">{m.yourSelection()}</div>
		<div class="px-2 mx-2 text-sm">
			<i class="fa-solid fa-info-circle mr-2"></i>{m.composerHint()}
		</div>
	</div>
	<div class="card p-4 bg-white shadow">
		<div class="p-2 font-semibold text-lg">
			{riskData.risk_assessment_objects.length <= 1
				? m.composerTitle()
				: m.composerTitlePlural({ number: riskData.risk_assessment_objects.length })}:
		</div>
		<div class="flex space-x-2">
			<div class="w-1/3">
				<div>
					<div class="p-2 text-sm font-semibold">{m.currentRiskLevelPerScenario()}</div>

					<div class="items-center h-96">
						<DonutChart
							name="current_risk_level"
							s_label={m.currentRiskLevelPerScenario()}
							values={riskData.current_level}
							colors={riskData.current_level.map((object) => object.color)}
						/>
					</div>
				</div>
			</div>
			<div class="w-1/3">
				<div class="p-2 text-sm font-semibold">{m.statusOfAssociatedMeasures()}</div>
				<div>
					<div class="items-center justify-center h-96">
						<BarChart
							name="composer"
							labels={riskData.applied_control_status.labels}
							values={riskData.applied_control_status.values}
						/>
					</div>
				</div>
			</div>
			<div class="w-1/3">
				<div class="p-2 text-sm font-semibold">{m.residualRiskLevelPerScenario()}</div>
				<div class="items-center h-96">
					<DonutChart
						name="residual_risk_level"
						s_label={m.residualRiskLevelPerScenario()}
						values={riskData.residual_level}
						colors={riskData.residual_level.map((object) => object.color)}
					/>
				</div>
			</div>
		</div>
		<div class="bg-zinc-100 shadow rounded p-3 flex flex-col space-y-2">
			<div>
				<i class="far fa-lightbulb mr-1"></i>&nbsp;<span class="font-semibold"
					>{m.forTheSelectedScope()}:</span
				>
			</div>
			<ul class="list-disc px-6">
				<li>
					{m.untreatedRiskScenarios({
						count: riskData.counters.untreated,
						s: riskData.counters.untreated > 1 ? 's' : ''
					})}
					<ul class="list-circle ml-4">
						{#each riskData.riskscenarios.untreated as scenario}
							<li>{scenario.name}</li>
						{/each}
					</ul>
				</li>
				<li>
					{m.acceptedRiskScenarios({
						count: riskData.counters.accepted,
						s: riskData.counters.accepted > 1 ? 's' : ''
					})}
					<ul class="list-circle ml-4">
						{#each riskData.riskscenarios.accepted as scenario}
							<li>{scenario.name}</li>
						{/each}
					</ul>
				</li>
			</ul>
		</div>
	</div>
	<!-- SECOND PART -->
	<div class="flex flex-col space-y-2">
		{#each riskData.risk_assessment_objects as item}
			<div>
				<div class="card bg-white overflow-hidden shadow" id="headingOne">
					<div
						class="flex flex-row space-x-4 px-8 py-4 w-full hover:bg-gray-100 cursor-pointer items-center"
						onclick={() => {
							item.show = !item.show;
						}}
						role="button"
						tabindex="0"
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') item.show = !item.show;
						}}
					>
						<div class="text-gray-700">
							{#if item.show}
								<i class="fas fa-angle-up"></i>
							{:else}
								<i class="fas fa-angle-down"></i>
							{/if}
						</div>
						<button class="text-gray-700 font-semibold focus:outline-none" type="button">
							{item.risk_assessment.perimeter.str}/{item.risk_assessment.name}
						</button>
						<div>
							{#if item.risk_assessment.quality_check.count > 0}
								<span class="text-xs px-2 py-1 rounded bg-orange-200 shadow"
									>{m.reviewNeeded()}</span
								>
							{:else}
								<span class="text-xs px-2 py-1 rounded bg-green-200 shadow">{m.ok()}</span>
							{/if}
						</div>
					</div>
					{#if item.show}
						<div class="border-t px-10 py-4 bg-white flex flex-row space-x-4">
							<div>
								<div class="pb-2">
									{#if item.risk_assessment.quality_check.count > 0}
										➡️ <span class="text-sm"
											>{m.inconsistenciesFoundComposer({
												count: item.risk_assessment.quality_check.count,
												s: item.risk_assessment.quality_check.count > 1 ? 's' : '',
												plural: item.risk_assessment.quality_check.count > 1 ? 'ies' : 'y'
											})}
											<a class="simple-link hover:underline visited:text-indigo-600" href="/x-rays"
												>x-rays</a
											></span
										>.
									{/if}
								</div>
								<div>
									<table class="border border-collapse my-2 p-2 rounded">
										<thead>
											<tr>
												<th class="border p-2 bg-gray-200"></th>
												<th class="border p-2 bg-gray-200">{m.current()}</th>
												<th class="border p-2 bg-gray-200">{m.residual()}</th>
											</tr>
										</thead>
										<tbody>
											{#each item.synth_table as lvl}
												<tr>
													<td class="border p-2" style="background-color: {lvl.color}">{lvl.lvl}</td
													>
													<td class="border p-2 text-center">{lvl.current}</td>
													<td class="border p-2 text-center">{lvl.residual}</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>

								<div>
									<a
										class="text-indigo-800 hover:text-indigo-600 py-2 my-2"
										href="/risk-assessments/{item.risk_assessment.id}/"
										><i class="fas fa-external-link-square-alt"></i> {m.jumpToRiskAssessment()}</a
									>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/each}
	</div>
</div>
