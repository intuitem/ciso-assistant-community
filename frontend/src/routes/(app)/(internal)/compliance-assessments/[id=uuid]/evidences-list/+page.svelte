<script lang="ts">
	import { page } from '$app/state';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { m } from '$paraglide/messages';
	let { data } = $props();

	const evidencesHead = {
		name: 'name',
		status: 'status',
		last_update: 'updatedAt',
		expiry_date: 'expiryDate',
		owner: 'owner',
		requirement_assessments: 'matchingRequirements'
	};

	const evidences: TableSource = {
		head: evidencesHead,
		body: [],
		meta: []
	};
</script>

<div class="bg-white p-2 shadow-sm rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{m.perimeter()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/perimeters/{data.compliance_assessment.perimeter.id}/"
			>{data.compliance_assessment.perimeter.str}</a
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

<div class="flex flex-col space-y-4 bg-white p-4 shadow-sm rounded-lg space-x-2">
	<div>
		<p class="text-xl font-extrabold">{m.associatedEvidences()}</p>
		<p class="text-sm text-gray-500">
			{m.evidencesHelpText()}
		</p>
	</div>
	<div class="">
		<ModelTable
			URLModel="evidences"
			source={evidences}
			search={true}
			rowsPerPage={true}
			orderBy={{ identifier: 'name', direction: 'asc' }}
			baseEndpoint="/compliance-assessments/{page.params.id}/evidences-list"
			fields={['name', 'status', 'last_update', 'expiry_date', 'owner', 'requirement_assessments']}
		/>
	</div>
</div>
