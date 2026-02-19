<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { goto } from '$app/navigation';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import ActivityTracker from '$lib/components/DataViz/ActivityTracker.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { listViewFields } from '$lib/utils/table';

	let { data }: { data: PageData } = $props();

	const appliedControlFilters = listViewFields['applied-controls'].filters;
	const APPLIED_CONTROL_FILTERS = {
		status: appliedControlFilters.status,
		priority: appliedControlFilters.priority,
		folder: appliedControlFilters.folder
	};

	let showEmptySections = $state(false);

	function buildMultiParam(key: string, values: string[]): string {
		if (!values || values.length === 0) return '';
		return values.map((v) => `${key}=${v}`).join('&');
	}

	let actorIds = $derived(data.actorIds || []);
	let ownerParams = $derived(buildMultiParam('owner', actorIds));
	let ownersParams = $derived(buildMultiParam('owners', actorIds));
	let authorsParams = $derived(buildMultiParam('authors', actorIds));
	let assignedToParams = $derived(buildMultiParam('assigned_to', actorIds));

	function toggleTeamAssignments() {
		goto(`/my-assignments?include_teams=${!data.includeTeams}`, { invalidateAll: true });
	}
</script>

<div class="flex items-center justify-between p-2 mb-2">
	<h2 class="text-xl font-semibold">{m.myAssignments()}</h2>
	<div class="flex gap-2">
		<button type="button" class="btn btn-sm variant-ghost-surface" onclick={toggleTeamAssignments}>
			<i class="fa-solid {data.includeTeams ? 'fa-user' : 'fa-users'} mr-2"></i>
			{data.includeTeams ? m.directAssignmentsOnly() : m.includeTeamAssignments()}
		</button>
		<button
			type="button"
			class="btn btn-sm variant-ghost-surface"
			onclick={() => (showEmptySections = !showEmptySections)}
		>
			<i class="fa-solid {showEmptySections ? 'fa-eye-slash' : 'fa-eye'} mr-2"></i>
			{showEmptySections ? m.hideEmptySections() : m.showEmptySections()}
		</button>
	</div>
</div>

{#await data.stream.counts}
	<div class="flex items-center justify-center p-8">
		<LoadingSpinner />
	</div>
{:then counts}
	<div class="grid grid-cols-12 gap-4 p-2">
		<div class="col-span-7 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
			<div class="font-bold mb-2">
				<i class="fa-solid fa-fire-extinguisher mr-2"></i>{m.appliedControls()}
				{#if counts.appliedControls > 0}
					<span class="badge variant-filled-surface ml-2">{counts.appliedControls}</span>
				{/if}
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
				baseEndpoint="/applied-controls?{ownerParams}"
			/>
		</div>
		<div class="col-span-5 p-2 flex items-center justify-center">
			<ActivityTracker metrics={data.data.metrics} />
		</div>
		{#if showEmptySections || counts.tasks > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-note-sticky mr-2"></i>{m.tasks()}
					{#if counts.tasks > 0}
						<span class="badge variant-filled-surface ml-2">{counts.tasks}</span>
					{/if}
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
					baseEndpoint="/task-templates?{assignedToParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.complianceAssessments > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-certificate mr-2"></i>{m.complianceAssessments()}
					{#if counts.complianceAssessments > 0}
						<span class="badge variant-filled-surface ml-2">{counts.complianceAssessments}</span>
					{/if}
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
					baseEndpoint="/compliance-assessments?{authorsParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.riskAssessments > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-magnifying-glass-chart mr-2"></i>{m.riskAssessments()}
					{#if counts.riskAssessments > 0}
						<span class="badge variant-filled-surface ml-2">{counts.riskAssessments}</span>
					{/if}
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
					baseEndpoint="/risk-assessments?{authorsParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.riskScenarios > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-clone mr-2"></i>{m.riskScenarios()}
					{#if counts.riskScenarios > 0}
						<span class="badge variant-filled-surface ml-2">{counts.riskScenarios}</span>
					{/if}
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
					baseEndpoint="/risk-scenarios?{ownerParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.incidents > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-bug mr-2"></i>{m.incidents()}
					{#if counts.incidents > 0}
						<span class="badge variant-filled-surface ml-2">{counts.incidents}</span>
					{/if}
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
					baseEndpoint="/incidents?{ownersParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.securityExceptions > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-circle-exclamation mr-2"></i>{m.securityExceptions()}
					{#if counts.securityExceptions > 0}
						<span class="badge variant-filled-surface ml-2">{counts.securityExceptions}</span>
					{/if}
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
					baseEndpoint="/security-exceptions?{ownersParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.findingsAssessments > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-clipboard-list mr-2"></i>{m.findingsAssessments()}
					{#if counts.findingsAssessments > 0}
						<span class="badge variant-filled-surface ml-2">{counts.findingsAssessments}</span>
					{/if}
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
					baseEndpoint="/findings-assessments?{authorsParams}"
				/>
			</div>
		{/if}
		{#if (showEmptySections || counts.validationFlows > 0) && data.featureflags?.validation_flows}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-check-circle mr-2"></i>{m.validationFlows()}
					{#if counts.validationFlows > 0}
						<span class="badge variant-filled-surface ml-2">{counts.validationFlows}</span>
					{/if}
				</div>
				<ModelTable
					source={{
						head: {
							ref_id: 'ref_id',
							status: 'status',
							created_at: 'created_at',
							requester: 'requester',
							folder: 'folder'
						},
						body: []
					}}
					hideFilters={true}
					URLModel="validation-flows"
					baseEndpoint="/validation-flows?approver={data.user.id}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.findings > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-triangle-exclamation mr-2"></i>{m.findings()}
					{#if counts.findings > 0}
						<span class="badge variant-filled-surface ml-2">{counts.findings}</span>
					{/if}
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
					baseEndpoint="/findings?{ownerParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.organisationObjectives > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-bullseye mr-2"></i>{m.organisationObjectives()}
					{#if counts.organisationObjectives > 0}
						<span class="badge variant-filled-surface ml-2">{counts.organisationObjectives}</span>
					{/if}
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
					baseEndpoint="/organisation-objectives?{assignedToParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.rightRequests > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-user-shield mr-2"></i>{m.rightRequests()}
					{#if counts.rightRequests > 0}
						<span class="badge variant-filled-surface ml-2">{counts.rightRequests}</span>
					{/if}
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
					baseEndpoint="/right-requests?{ownerParams}"
				/>
			</div>
		{/if}
		{#if showEmptySections || counts.metricInstances > 0}
			<div class="col-span-6 bg-surface-50-950 border border-surface-200-800 p-2 rounded">
				<div class="font-bold mb-2">
					<i class="fa-solid fa-chart-line mr-2"></i>{m.metricInstances()}
					{#if counts.metricInstances > 0}
						<span class="badge variant-filled-surface ml-2">{counts.metricInstances}</span>
					{/if}
				</div>
				<ModelTable
					source={{
						head: {
							ref_id: 'ref_id',
							name: 'name',
							status: 'status',
							current_value: 'current_value',
							folder: 'folder'
						},
						body: []
					}}
					hideFilters={true}
					URLModel="metric-instances"
					baseEndpoint="/metric-instances?{ownerParams}"
				/>
			</div>
		{/if}
	</div>
{/await}
