<script lang="ts">
	import { page } from '$app/stores';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { m } from '$paraglide/messages';
	import { tableSourceMapper } from '@skeletonlabs/skeleton';

	export let data;

	const appliedControlsHead = {
		name: 'name',
		status: 'status',
		priority: 'priority',
		category: 'category',
		csf_function: 'csfFunction',
		eta: 'eta',
		expiry_date: 'expiryDate',
		effort: 'effort',
		cost: 'cost',
		'risk-scenarios': 'matchingScenarios'
	};

	const appliedControls: TableSource = {
		head: appliedControlsHead,
		body: [],
		meta: []
	};
</script>

<div class="bg-white p-2 shadow rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{m.perimeter()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/perimeters/{data.risk_assessment.perimeter.id}/"
			>{data.risk_assessment.perimeter.str}</a
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
<div class="flex flex-col space-y-4 bg-white p-4 shadow rounded-lg space-x-2">
	<div>
		<p class="text-xl font-extrabold">{m.associatedAppliedControls()}</p>
		<p class="text-sm text-gray-500">
			{m.actionPlanHelpText()}
		</p>
	</div>
	<div class="">
		<ModelTable
			URLModel="applied-controls"
			source={appliedControls}
			search={true}
			rowsPerPage={true}
			orderBy={{ identifier: 'eta', direction: 'desc' }}
			baseEndpoint="/risk-assessments/{$page.params.id}/action-plan"
			fields={[
				'name',
				'status',
				'priority',
				'category',
				'csf_function',
				'eta',
				'expiry_date',
				'effort',
				'cost',
				'risk_scenarios'
			]}
		/>
	</div>
</div>
