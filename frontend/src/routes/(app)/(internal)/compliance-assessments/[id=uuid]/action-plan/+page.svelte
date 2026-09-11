<script lang="ts">
	import { page } from '$app/state';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import ActionPlanBudgetOverview from '$lib/components/DataViz/ActionPlanBudgetOverview.svelte';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	let { data } = $props();

	let activeTab = $state('applied-controls');

	// The promise made about each task is part of the plan, so it earns a column
	// wherever the feature is on.
	const showCommitment = $derived(!!page.data?.featureflags?.commitment_management);

	// The head is the universe the column picker offers, so the commitment columns must
	// leave it with the flag — otherwise they are pickable and render blank.
	const withoutCommitment = (head: Record<string, string>) =>
		Object.fromEntries(
			Object.entries(head).filter(([key]) => !['commitment_state', 'committed_eta'].includes(key))
		);

	const appliedControlsHead = {
		ref_id: 'refId',
		name: 'name',
		status: 'status',
		priority: 'priority',
		category: 'category',
		csf_function: 'csfFunction',
		owner: 'owner',
		eta: 'eta',
		expiry_date: 'expiryDate',
		control_impact: 'controlImpact',
		effort: 'effort',
		annual_cost: 'cost',
		requirement_assessments: 'matchingRequirements',
		created_at: 'createdAt',
		updated_at: 'updatedAt'
	};

	const taskTemplatesHeadAll: Record<string, string> = {
		ref_id: 'refId',
		name: 'name',
		description: 'description',
		requirement_assessments: 'matchingRequirements',
		assigned_to: 'assigned_to',
		// TaskTemplate has no `eta`; `task_date` is the date it promises, and the
		// commitment machinery freezes that same field for this model.
		task_date: 'eta',
		status: 'status',
		commitment_state: 'commitment',
		committed_eta: 'committedDate',
		is_recurrent: 'is_recurrent',
		next_occurrence: 'nextOccurrence',
		next_occurrence_status: 'nextOccurrenceStatus',
		folder: 'domain',
		created_at: 'createdAt',
		updated_at: 'updatedAt'
	};

	const taskTemplatesHead = $derived(
		showCommitment ? taskTemplatesHeadAll : withoutCommitment(taskTemplatesHeadAll)
	);

	const taskTemplatesColumns = $derived([
		'ref_id',
		'name',
		'requirement_assessments',
		'assigned_to',
		'task_date',
		...(showCommitment ? ['commitment_state'] : []),
		'status'
	]);

	const appliedControls: TableSource = {
		head: appliedControlsHead,
		body: [],
		meta: []
	};

	const taskTemplates: TableSource = $derived({
		head: taskTemplatesHead,
		body: [],
		meta: []
	});

	const tabClass =
		'px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500';
</script>

<div class="bg-surface-50-950 p-2 shadow-sm rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{#if data.compliance_assessment.perimeter}
			{m.perimeter()}:
			<a
				class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
				href="/perimeters/{data.compliance_assessment.perimeter.id}/"
				>{data.compliance_assessment.perimeter.str}</a
			>
		{:else}
			{m.folder()}:
			<a
				class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
				href="/folders/{data.compliance_assessment.folder.id}/"
				>{data.compliance_assessment.folder.str}</a
			>
		{/if}
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

<div class="bg-surface-50-950 shadow-sm rounded-lg">
	<Tabs value={activeTab} onValueChange={(e) => (activeTab = e.value)} class="w-full">
		<Tabs.List class="border-b border-surface-200-800 px-4">
			<Tabs.Trigger value="applied-controls" class={tabClass}>
				<i class="fa-solid fa-shield-halved mr-2"></i>{m.appliedControls()}
			</Tabs.Trigger>
			<Tabs.Trigger value="task-templates" class={tabClass}>
				<i class="fa-solid fa-list-check mr-2"></i>{m.taskTemplates()}
			</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content value="applied-controls" class="p-4 space-y-4">
			<ActionPlanBudgetOverview
				budgetEndpoint={`/compliance-assessments/${page.params.id}/action-plan/budget-overview`}
			/>
			<div class="flex justify-between items-center w-full">
				<div class="flex-1">
					<p class="text-xl font-extrabold">{m.associatedAppliedControls()}</p>
					<p class="text-sm text-surface-600-400">
						{m.actionPlanHelpText()}
					</p>
				</div>
				<div class="flex gap-2 ml-auto items-center">
					<Anchor
						breadcrumbAction="push"
						href={`/compliance-assessments/${page.params.id}/action-plan/analytics`}
						label={m.analytics()}
						class="btn text-gray-100 bg-linear-to-r from-sky-500 to-cyan-500 h-fit"
						title={m.appliedControlsAnalytics()}
						aria-label={m.appliedControlsAnalytics()}
						data-testid="analytics-button"
						><i class="fa-solid fa-chart-pie mr-2" aria-hidden="true"></i>{m.analytics()}</Anchor
					>
					<Anchor
						breadcrumbAction="push"
						href={`/applied-controls/flash-mode?compliance_assessments=${page.params.id}&backUrl=${encodeURIComponent(page.url.pathname)}&backLabel=${encodeURIComponent(m.actionPlan())}`}
						class="btn text-gray-100 bg-linear-to-r from-indigo-500 to-violet-500 h-fit"
						><i class="fa-solid fa-bolt mr-2" aria-hidden="true"></i> {m.flashMode()}</Anchor
					>
				</div>
			</div>
			<ModelTable
				URLModel="applied-controls"
				source={appliedControls}
				search={true}
				rowsPerPage={true}
				orderBy={{ identifier: 'eta', direction: 'desc' }}
				baseEndpoint="/compliance-assessments/{page.params.id}/action-plan"
				columnSelector={true}
				columnStateKey="applied-controls:compliance-action-plan"
				fields={[
					'ref_id',
					'name',
					'status',
					'priority',
					'category',
					'csf_function',
					'owner',
					'eta',
					'expiry_date',
					'control_impact',
					'effort',
					'annual_cost',
					'requirement_assessments'
				]}
			/>
		</Tabs.Content>

		<Tabs.Content value="task-templates" class="p-4 space-y-4">
			<div class="flex justify-between items-center w-full">
				<div class="flex-1">
					<p class="text-xl font-extrabold">{m.associatedTaskTemplates()}</p>
					<p class="text-sm text-surface-600-400">
						{m.auditActionPlanTasksHelpText()}
					</p>
				</div>
				<div class="flex gap-2 ml-auto items-center">
					<Anchor
						breadcrumbAction="push"
						href={`/task-templates/analytics?compliance_assessments=${page.params.id}&backUrl=${encodeURIComponent(page.url.pathname)}&backLabel=${encodeURIComponent(m.actionPlan())}`}
						label={m.analytics()}
						class="btn text-gray-100 bg-linear-to-r from-sky-500 to-cyan-500 h-fit"
						title={m.taskTemplatesAnalytics()}
						aria-label={m.taskTemplatesAnalytics()}
						data-testid="task-analytics-button"
						><i class="fa-solid fa-chart-pie mr-2" aria-hidden="true"></i>{m.analytics()}</Anchor
					>
				</div>
			</div>
			{#key showCommitment}
				<ModelTable
					URLModel="task-templates"
					source={taskTemplates}
					search={true}
					rowsPerPage={true}
					orderBy={{ identifier: 'task_date', direction: 'desc' }}
					tags={false}
					baseEndpoint="/task-templates?compliance_assessments={page.params.id}"
					columnSelector={true}
					columnStateKey="task-templates:compliance-action-plan"
					fields={taskTemplatesColumns}
				/>
			{/key}
		</Tabs.Content>
	</Tabs>
</div>
