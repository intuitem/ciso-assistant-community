<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import ActivityTracker from '$lib/components/DataViz/ActivityTracker.svelte';
	import { listViewFields } from '$lib/utils/table';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const appliedControlFilters = listViewFields['applied-controls'].filters;
	const APPLIED_CONTROL_FILTERS = {
		status: appliedControlFilters.status,
		priority: appliedControlFilters.priority,
		folder: appliedControlFilters.folder
	};
</script>

<div class="grid grid-cols-12 gap-4 p-2">
	<div class="col-span-7 bg-linear-to-br from-pink-200 to-pink-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-fire-extinguisher mr-2" />{m.appliedControls()}
		</div>
		<ModelTable
			source={{
				head: {
					ref_id: 'ref_id',
					name: 'name',
					status: 'status',
					priority: 'priority',
					eta: 'eta',
					folder: 'folder'
				},
				body: [],
				filters: APPLIED_CONTROL_FILTERS
			}}
			URLModel="applied-controls"
			baseEndpoint="/applied-controls?owner={data.user.id}"
		/>
	</div>
	<div class="col-span-5 p-2 flex items-center justify-center">
		<ActivityTracker metrics={data.data.metrics} />
	</div>
	<div class="col-span-6 bg-linear-to-br from-violet-200 to-violet-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-note-sticky mr-2" />{m.tasks()}
		</div>
		<ModelTable
			source={{
				head: {
					name: 'name',
					status: 'status',
					is_recurrent: 'is_recurrent',
					next_occurrence: 'next_occurrence'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="task-templates"
			baseEndpoint="/task-templates?assigned_to={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-blue-200 to-blue-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-certificate mr-2" />{m.complianceAssessments()}
		</div>
		<ModelTable
			source={{
				head: {
					name: 'name',
					status: 'status',
					eta: 'eta',
					progress: 'progress',
					perimeter: 'perimeter'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="compliance-assessments"
			baseEndpoint="/compliance-assessments?authors={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-blue-200 to-blue-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-magnifying-glass-chart mr-2" />{m.riskAssessments()}
		</div>
		<ModelTable
			source={{
				head: {
					name: 'name',
					status: 'status',
					eta: 'eta',
					perimeter: 'perimeter'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="risk-assessments"
			baseEndpoint="/risk-assessments?authors={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-violet-200 to-violet-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-clone mr-2" />{m.riskScenarios()}
		</div>
		<ModelTable
			source={{
				head: {
					ref_id: 'ref_id',
					name: 'name',
					current_level: 'current_level',
					residual_level: 'residual_level',
					risk_assessment: 'risk_assessment'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="risk-scenarios"
			baseEndpoint="/risk-scenarios?owner={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-violet-200 to-violet-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-bug mr-2" />{m.incidents()}
		</div>
		<ModelTable
			source={{
				head: {
					ref_id: 'ref_id',
					name: 'name',
					status: 'status',
					severity: 'severity',
					folder: 'folder'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="incidents"
			baseEndpoint="/incidents?owners={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-blue-200 to-blue-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-circle-exclamation mr-2" />{m.securityExceptions()}
		</div>
		<ModelTable
			source={{
				head: {
					name: 'name',
					status: 'status',
					severity: 'severity',
					expiration_date: 'expiration_date',
					folder: 'folder'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="security-exceptions"
			baseEndpoint="/security-exceptions?owners={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-blue-200 to-blue-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-clipboard-list mr-2" />{m.findingsAssessments()}
		</div>
		<ModelTable
			source={{
				head: {
					name: 'name',
					status: 'status',
					category: 'category',
					perimeter: 'perimeter'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="findings-assessments"
			baseEndpoint="/findings-assessments?authors={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-violet-200 to-violet-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-triangle-exclamation mr-2" />{m.findings()}
		</div>
		<ModelTable
			source={{
				head: {
					ref_id: 'ref_id',
					name: 'name',
					severity: 'severity',
					status: 'status'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="findings"
			baseEndpoint="/findings?owner={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-green-200 to-green-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-bullseye mr-2" />{m.organisationObjectives()}
		</div>
		<ModelTable
			source={{
				head: {
					ref_id: 'ref_id',
					name: 'name',
					status: 'status',
					health: 'health',
					folder: 'folder'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="organisation-objectives"
			baseEndpoint="/organisation-objectives?assigned_to={data.user.id}"
		/>
	</div>
	<div class="col-span-6 bg-linear-to-br from-orange-200 to-orange-50 p-2 rounded">
		<div class="font-bold mb-2">
			<i class="fa-solid fa-user-shield mr-2" />{m.rightRequests()}
		</div>
		<ModelTable
			source={{
				head: {
					ref_id: 'ref_id',
					name: 'name',
					request_type: 'request_type',
					status: 'status',
					due_date: 'due_date'
				},
				body: []
			}}
			hideFilters={true}
			URLModel="right-requests"
			baseEndpoint="/right-requests?owner={data.user.id}"
		/>
	</div>
</div>
