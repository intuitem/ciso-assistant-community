<script lang="ts">
	import { tableSourceMapper } from '$lib/utils/table';
	import { page } from '$app/state';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';

	let { data } = $props();

	let activeTab = $state('applied-controls');

	// The promise made about each remediation is part of the plan, so it earns a column
	// wherever the feature is on.
	const showCommitment = $derived(!!page.data?.featureflags?.commitment_management);

	// The head is the universe the column picker offers, so the commitment columns must
	// leave it with the flag — otherwise they are pickable and render blank.
	const withoutCommitment = (head: Record<string, string>) =>
		Object.fromEntries(
			Object.entries(head).filter(([key]) => !['commitment_state', 'committed_eta'].includes(key))
		);

	const appliedControlsHeadAll: Record<string, string> = {
		ref_id: 'refId',
		name: 'name',
		description: 'description',
		findings: 'associated_findings',
		owner: 'owner',
		status: 'status',
		priority: 'priority',
		category: 'category',
		csf_function: 'csfFunction',
		eta: 'eta',
		expiry_date: 'expiryDate',
		effort: 'effort',
		annual_cost: 'cost',
		commitment_state: 'commitment',
		committed_eta: 'committedDate',
		created_at: 'createdAt',
		updated_at: 'updatedAt'
	};

	const taskTemplatesHeadAll: Record<string, string> = {
		ref_id: 'refId',
		name: 'name',
		description: 'description',
		findings: 'associated_findings',
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

	const appliedControlsHead = $derived(
		showCommitment ? appliedControlsHeadAll : withoutCommitment(appliedControlsHeadAll)
	);
	const taskTemplatesHead = $derived(
		showCommitment ? taskTemplatesHeadAll : withoutCommitment(taskTemplatesHeadAll)
	);

	// Kept to the key facts; the rest stays one click away in the column picker.
	const appliedControlsColumns = $derived([
		'ref_id',
		'name',
		'description',
		'findings',
		'owner',
		'eta',
		...(showCommitment ? ['commitment_state'] : []),
		'status'
	]);

	const taskTemplatesColumns = $derived([
		'ref_id',
		'name',
		'description',
		'findings',
		'assigned_to',
		'task_date',
		...(showCommitment ? ['commitment_state'] : []),
		'status'
	]);

	const appliedControls: TableSource = $derived({
		head: appliedControlsHead,
		body: tableSourceMapper([], appliedControlsColumns),
		meta: []
	});

	const taskTemplates: TableSource = $derived({
		head: taskTemplatesHead,
		body: tableSourceMapper([], taskTemplatesColumns),
		meta: []
	});

	const tabClass =
		'px-4 py-3 text-sm font-medium text-surface-600-400 hover:text-surface-700-300 border-b-2 border-transparent transition-colors aria-[selected=true]:!text-primary-700 aria-[selected=true]:!border-primary-500';
</script>

<div class="bg-surface-50-950 p-2 shadow-sm rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{#if data.findings_assessment.perimeter}
			{m.perimeter()}:
			<a
				class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
				href="/perimeters/{data.findings_assessment.perimeter.id}/"
				>{data.findings_assessment.perimeter.str}</a
			>
		{:else}
			{m.folder()}:
			<a
				class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
				href="/folders/{data.findings_assessment.folder.id}/"
				>{data.findings_assessment.folder.str}</a
			>
		{/if}
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
						href={`/applied-controls/analytics?findings_assessments=${page.params.id}&backUrl=${encodeURIComponent(page.url.pathname)}&backLabel=${encodeURIComponent(m.actionPlan())}`}
						label={m.analytics()}
						class="btn text-gray-100 bg-linear-to-r from-sky-500 to-cyan-500 h-fit"
						title={m.appliedControlsAnalytics()}
						aria-label={m.appliedControlsAnalytics()}
						data-testid="analytics-button"
						><i class="fa-solid fa-chart-pie mr-2" aria-hidden="true"></i>{m.analytics()}</Anchor
					>
					<Anchor
						breadcrumbAction="push"
						href={`/applied-controls/flash-mode?findings_assessments=${page.params.id}&backUrl=${encodeURIComponent(page.url.pathname)}&backLabel=${encodeURIComponent(m.actionPlan())}`}
						class="btn text-gray-100 bg-linear-to-r from-indigo-500 to-violet-500 h-fit"
						><i class="fa-solid fa-bolt mr-2" aria-hidden="true"></i> {m.flashMode()}</Anchor
					>
				</div>
			</div>
			{#key showCommitment}
				<ModelTable
					URLModel="applied-controls"
					source={appliedControls}
					search={true}
					rowsPerPage={true}
					orderBy={{ identifier: 'eta', direction: 'desc' }}
					tags={false}
					baseEndpoint="/applied-controls?findings_assessments={page.params.id}"
					columnSelector={true}
					columnStateKey="applied-controls:findings-action-plan"
					fields={appliedControlsColumns}
				/>
			{/key}
		</Tabs.Content>

		<Tabs.Content value="task-templates" class="p-4 space-y-4">
			<div class="flex justify-between items-center w-full">
				<div class="flex-1">
					<p class="text-xl font-extrabold">{m.associatedTaskTemplates()}</p>
					<p class="text-sm text-surface-600-400">
						{m.findingsActionPlanTasksHelpText()}
					</p>
				</div>
				<div class="flex gap-2 ml-auto items-center">
					<Anchor
						breadcrumbAction="push"
						href={`/task-templates/analytics?findings_assessments=${page.params.id}&backUrl=${encodeURIComponent(page.url.pathname)}&backLabel=${encodeURIComponent(m.actionPlan())}`}
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
					baseEndpoint="/task-templates?findings_assessments={page.params.id}"
					columnSelector={true}
					columnStateKey="task-templates:findings-action-plan"
					fields={taskTemplatesColumns}
				/>
			{/key}
		</Tabs.Content>
	</Tabs>
</div>
