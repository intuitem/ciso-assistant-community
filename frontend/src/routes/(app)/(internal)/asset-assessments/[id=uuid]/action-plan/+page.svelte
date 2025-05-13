<script lang="ts">
	import { page } from '$app/stores';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { m } from '$paraglide/messages';
	import { tableSourceMapper } from '@skeletonlabs/skeleton';

	let { data } = $props();

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
		findings_count: 'associated_findings'
	};
	const appliedControlsColumns = [
		'name',
		'status',
		'priority',
		'category',
		'csf_function',
		'eta',
		'expiry_date',
		'effort',
		'cost',
		'findings_count'
	];

	const appliedControls: TableSource = {
		head: appliedControlsHead,
		body: tableSourceMapper([], appliedControlsColumns),
		meta: []
	};
</script>

<div class="bg-white p-2 shadow rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{m.perimeter()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/perimeters/{data.findings_assessment.perimeter.id}/"
			>{data.findings_assessment.perimeter.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.findingsAssessment()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/findings-assessments/{data.findings_assessment.id}/"
			>{data.findings_assessment.name} - {data.findings_assessment.version}</a
		>
	</p>
	<p>/</p>
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
			tags={false}
			baseEndpoint="/applied-controls?findings_assessments={$page.params.id}"
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
				'findings_count'
			]}
		/>
	</div>
</div>
