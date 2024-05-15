<script lang="ts">
	import { goto } from '$app/navigation';
	import * as m from '$paraglide/messages.js';

	export let data;

	const scenarioTreatmentColorMap = (status: string) => {
		const map: Record<string, string> = {
			open: 'bg-orange-200',
			mitigate: 'bg-green-200',
			accept: 'bg-sky-200',
			avoid: 'bg-red-200',
			transfer: 'bg-violet-200'
		};
		return map[status.toLowerCase()] ?? 'bg-gray-200';
	};

	const measureStatusColorMap = (treatment: string) => {
		const map: Record<string, string> = {
			'--': 'bg-gray-200',
			planned: 'bg-blue-200',
			inactive: 'bg-red-200',
			active: 'bg-green-200'
		};
		if (treatment !== null) {
			return map[treatment.toLowerCase()];
		} else {
			return 'bg-gray-200';
		}
	};
</script>

<div class="bg-white p-2 m-2 shadow rounded-lg space-x-2 flex flex-row justify-center">
	<p class="font-semibold text-lg">
		{m.project()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/projects/{data.risk_assessment.project.id}/">{data.risk_assessment.project.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.riskAssessment()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/risk-assessments/{data.risk_assessment.id}/"
			>{data.risk_assessment.name} - {data.risk_assessment.version}</a
		>
	</p>
</div>

<p class="p-2 m-2 text-lg font-semibold">{m.associatedRiskScenarios()}:</p>

<div class="bg-white p-2 m-2 shadow overflow-hidden rounded-lg flex">
	<table class="w-full p-2 mt-2">
		<thead />
		<tbody>
			{#each data.risk_assessment.risk_scenarios as scenario}
				<tr class="bg-gray-100">
					<td class="text-lg p-3" colspan="9">
						<a
							class="unstyled text-primary-500 hover:text-primary-700"
							href="/risk-scenarios/{scenario.id}">{scenario.name}</a
						>
						<span class="badge {scenarioTreatmentColorMap(scenario.treatment)}"
							>{scenario.treatment}</span
						>
					</td>
				</tr>
				{#if scenario.existing_controls}
					<tr>
						<td class="text-md pl-6 pb-3 font-medium" colspan="9"> {m.existingControls()}: </td>
					</tr>
					<tr>
						<td class="text-sm pl-6 pb-3" colspan="9"> {scenario.existing_controls} </td>
					</tr>
				{/if}

				{#if scenario.applied_controls.length > 0}
					<tr>
						<td class="text-md pl-6 pb-3 font-medium" colspan="9"> {m.additionalMeasures()}: </td>
					</tr>
					<tr class="text-sm uppercase">
						<td class="px-2 text-center">#</td>
						<td class="px-2 font-semibold">{m.name()}</td>
						<td class="px-2 font-semibold">{m.description()}</td>
						<td class="px-2 font-semibold">{m.category()}</td>
						<td class="px-2 font-semibold">{m.referenceControl()}</td>
						<td class="px-2 font-semibold">{m.eta()}</td>
						<td class="px-2 font-semibold">{m.effort()}</td>
						<td class="px-2 font-semibold text-center">{m.link()}</td>
						<td class="px-2 font-semibold text-center">{m.status()}</td>
					</tr>
					{#each scenario.applied_controls as measure, index}
						<tr
							class="hover:text-primary-500 border-b cursor-pointer hover:scale-[0.99] duration-200"
							on:click={(_) => goto(`/applied-controls/${measure.id}`)}
						>
							<td class="px-2 py-3 text-center pl-4">M.{index + 1}</td>
							<td class="px-2 py-3">{measure.name ?? '--'}</td>
							<td class="px-2 py-3 max-w-md">{measure.description ?? '--'}</td>
							<td class="px-2 py-3">{measure.category ?? '--'}</td>
							<td class="px-2 py-3"
								>{measure.reference_control ? measure.reference_control.str : '--'}</td
							>
							<td class="px-2 py-3">{measure.eta ?? '--'}</td>
							<td class="px-2 py-3">{measure.effort ?? '--'}</td>
							<td class="px-2 py-3 text-center">{measure.link ?? '--'} </td>
							<td class="text-center"
								><span
									class="text-xs text-gray-900 whitespace-nowrap text-center p-1 mx-1 rounded {measureStatusColorMap(
										measure.status ?? '--'
									)}"
									>{measure.status ?? '--'}
								</span></td
							>
						</tr>
					{/each}
				{/if}

				{#if !scenario.existing_controls && !(scenario.applied_controls.length > 0)}
					<tr>
						<td colspan="9" class="p-2 text-left">
							<i class="fas fa-exclamation-circle" />
							{m.noAppliedControlYet()}
						</td>
					</tr>
				{/if}
			{/each}
		</tbody>
	</table>
</div>
