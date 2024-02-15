<script lang="ts">
	import { goto } from '$app/navigation';

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
			open: 'bg-orange-200',
			'in progress': 'bg-blue-200',
			'on hold': 'bg-red-200',
			done: 'bg-success-200'
		};
		return map[treatment.toLowerCase()] ?? 'bg-gray-200';
	};
</script>

<div class="bg-white p-2 m-2 shadow rounded-lg space-x-2 flex flex-row justify-center">
	<p class="font-semibold text-lg">
		Domain: <a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/folders/{data.risk_assessment.folder.id}/">{data.risk_assessment.folder.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		Project: <a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/projects/{data.risk_assessment.project.id}/">{data.risk_assessment.project.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		Risk assessment: <a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/risk-assessments/{data.risk_assessment.id}/"
			>{data.risk_assessment.name} - {data.risk_assessment.version}</a
		>
	</p>
</div>

<p class="p-2 m-2 text-lg font-semibold">Associated risk scenarios:</p>

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
				{#if scenario.existing_measures}
					<tr>
						<td class="text-md pl-6 pb-3 font-medium" colspan="9"> Existing measures: </td>
					</tr>
					<tr>
						<td class="text-sm pl-6 pb-3" colspan="9"> lorem ipsum </td>
					</tr>
				{/if}

				{#if scenario.security_measures.length > 0}
					<tr>
						<td class="text-md pl-6 pb-3 font-medium" colspan="9"> Additional measures: </td>
					</tr>
					<tr class="text-sm uppercase">
						<td class="px-2 text-center">#</td>
						<td class="px-2 font-semibold">Name</td>
						<td class="px-2 font-semibold">Description</td>
						<td class="px-2 font-semibold">Type</td>
						<td class="px-2 font-semibold">Security function</td>
						<td class="px-2 font-semibold">ETA</td>
						<td class="px-2 font-semibold">Effort</td>
						<td class="px-2 font-semibold text-center">Link</td>
						<td class="px-2 font-semibold text-center">Status</td>
					</tr>
					{#each scenario.security_measures as measure, index}
						<tr
							class="hover:text-primary-500 border-b cursor-pointer hover:scale-[0.99] duration-200"
							on:click={(_) => goto(`/security-measures/${measure.id}`)}
						>
							<td class="px-2 py-3 text-center pl-4">M.{index + 1}</td>
							<td class="px-2 py-3">{measure.name ?? '--'}</td>
							<td class="px-2 py-3 max-w-md">{measure.description ?? '--'}</td>
							<td class="px-2 py-3">{measure.type ?? '--'}</td>
							<td class="px-2 py-3">{measure.security_function.str ?? '--'}</td>
							<td class="px-2 py-3">{measure.eta ?? '--'}</td>
							<td class="px-2 py-3">{measure.effort ?? '--'}</td>
							<td class="px-2 py-3 text-center">{measure.link ?? '--'} </td>
							<td class="text-center"
								><span
									class="text-xs text-gray-900 whitespace-nowrap text-center p-1 mx-1 rounded {measureStatusColorMap(
										measure.status
									)}"
									>{measure.status}
								</span></td
							>
						</tr>
					{/each}
				{/if}

				{#if !scenario.existing_measures && !(scenario.security_measures.length > 0)}
					<tr>
						<td colspan="9" class="p-2 text-left">
							<i class="fas fa-exclamation-circle" /> No associated measure
						</td>
					</tr>
				{/if}
			{/each}
		</tbody>
	</table>
</div>
