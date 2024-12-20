<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import * as m from '$paraglide/messages.js';
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
		requirements_count: 'matchingRequirements'
	};
	const appliedControlsColums = [
		'name',
		'status',
		'priority',
		'category',
		'csf_function',
		'eta',
		'expiry_date',
		'effort',
		'cost',
		'requirements_count'
	];

	const AppliedControls: TableSource = {
		head: appliedControlsHead,
		body: tableSourceMapper(data.actionPlan, appliedControlsColums),
		meta: data.actionPlan
	};
</script>

<div class="bg-white p-2 shadow rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{m.project()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/projects/{data.compliance_assessment.project.id}/"
			>{data.compliance_assessment.project.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.complianceAssessment()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/compliance-assessments/{data.compliance_assessment.id}/"
			>{data.compliance_assessment.name} - {data.compliance_assessment.version}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.framework()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/frameworks/{data.compliance_assessment.framework.id}/"
			>{data.compliance_assessment.framework.str}</a
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
			source={AppliedControls}
			search={true}
			rowsPerPage={true}
			orderBy={{ identifier: 'eta', direction: 'desc' }}
			tags={false}
		/>
	</div>
</div>
