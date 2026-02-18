<script lang="ts">
	import { tableSourceMapper } from '$lib/utils/table';
	import { page } from '$app/state';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
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
		annual_cost: 'cost',
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
		'annual_cost',
		'findings_count'
	];

	const appliedControls: TableSource = {
		head: appliedControlsHead,
		body: tableSourceMapper([], appliedControlsColumns),
		meta: []
	};
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
<div class="flex flex-col space-y-4 bg-surface-50-950 p-4 shadow-sm rounded-lg space-x-2">
	<div class="flex justify-between items-center w-full">
		<div class="flex-1">
			<p class="text-xl font-extrabold">{m.associatedAppliedControls()}</p>
			<p class="text-sm text-surface-600-400">
				{m.actionPlanHelpText()}
			</p>
		</div>
		<div class="flex gap-2 ml-auto">
			<Anchor
				breadcrumbAction="push"
				href={`/applied-controls/flash-mode?findings_assessments=${page.params.id}&backUrl=${encodeURIComponent(page.url.pathname)}&backLabel=${encodeURIComponent(m.actionPlan())}`}
				class="btn text-surface-100-900 bg-linear-to-r from-indigo-500 to-violet-500 h-fit"
				><i class="fa-solid fa-bolt mr-2"></i> {m.flashMode()}</Anchor
			>
		</div>
	</div>
	<div class="">
		<ModelTable
			URLModel="applied-controls"
			source={appliedControls}
			search={true}
			rowsPerPage={true}
			orderBy={{ identifier: 'eta', direction: 'desc' }}
			tags={false}
			baseEndpoint="/applied-controls?findings_assessments={page.params.id}"
			fields={[
				'name',
				'status',
				'priority',
				'category',
				'csf_function',
				'eta',
				'expiry_date',
				'effort',
				'annual_cost',
				'findings_count'
			]}
		/>
	</div>
</div>
