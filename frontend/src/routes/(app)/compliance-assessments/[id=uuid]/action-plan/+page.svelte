<script lang="ts">
	import * as m from '$paraglide/messages.js';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { Tab, TabGroup, tableSourceMapper } from '@skeletonlabs/skeleton';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { breadcrumbObject } from '$lib/utils/stores';

	export let data;

	breadcrumbObject.set(data.compliance_assessment);

	let tabSet = 0;

	const toDoAppliedControls: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			eta: 'eta',
			expiry_date: 'expiryDate',
			effort: 'effort',
			requirements_count: 'matchingRequirements'
		},
		body: tableSourceMapper(data.actionPlan.to_do, [
			'name',
			'category',
			'csf_function',
			'eta',
			'expiry_date',
			'efforts',
			'requirements_count'
		]),
		meta: data.actionPlan.to_do
	};
	const inProgressAppliedControls: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			eta: 'eta',
			expiry_date: 'expiryDate',
			effort: 'effort',
			requirements_count: 'matchingRequirements'
		},
		body: tableSourceMapper(data.actionPlan.in_progress, [
			'name',
			'category',
			'csf_function',
			'eta',
			'expiry_date',
			'efforts',
			'requirements_count'
		]),
		meta: data.actionPlan.to_do
	};
	const onHoldAppliedControls: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			eta: 'eta',
			expiry_date: 'expiryDate',
			effort: 'effort',
			requirements_count: 'matchingRequirements'
		},
		body: tableSourceMapper(data.actionPlan.on_hold, [
			'name',
			'category',
			'csf_function',
			'eta',
			'expiry_date',
			'efforts',
			'requirements_count'
		]),
		meta: data.actionPlan.to_do
	};

	const activeAppliedControls: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			eta: 'eta',
			expiry_date: 'expiryDate',
			effort: 'effort',
			requirements_count: 'matchingRequirements'
		},
		body: tableSourceMapper(data.actionPlan.active, [
			'name',
			'category',
			'csf_function',
			'eta',
			'expiry_date',
			'efforts',
			'requirements_count'
		]),
		meta: data.actionPlan.active
	};

	const deprecatedAppliedControls: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			eta: 'eta',
			expiry_date: 'expiryDate',
			effort: 'effort',
			requirements_count: 'matchingRequirements'
		},
		body: tableSourceMapper(data.actionPlan.deprecated, [
			'name',
			'category',
			'csf_function',
			'eta',
			'expiry_date',
			'efforts',
			'requirements_count'
		]),
		meta: data.actionPlan.deprecated
	};

	const noneAppliedControls: TableSource = {
		head: {
			name: 'name',
			category: 'category',
			csf_function: 'csfFunction',
			eta: 'eta',
			expiry_date: 'expiryDate',
			effort: 'effort',
			requirements_count: 'matchingRequirements'
		},
		body: tableSourceMapper(data.actionPlan.none, [
			'name',
			'category',
			'csf_function',
			'eta',
			'expiry_date',
			'efforts',
			'requirements_count'
		]),
		meta: data.actionPlan.none
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
		<TabGroup>
			<Tab
				bind:group={tabSet}
				class="border-x border-t border-gray-300"
				active="bg-blue-200 border-b-2 border-blue-500"
				name="to_do"
				value={0}>{m.toDo()}</Tab
			>
			<Tab
				bind:group={tabSet}
				class="border-x border-t border-gray-300"
				active="bg-violet-400 border-b-2 border-blue-500"
				name="in_progress"
				value={1}>{m.inProgress()}</Tab
			>
			<Tab
				bind:group={tabSet}
				class="border-x border-t border-gray-300"
				active="bg-orange-300 border-b-2 border-blue-500"
				name="on_hold"
				value={2}>{m.onHold()}</Tab
			>
			<Tab
				bind:group={tabSet}
				class="border-x border-t border-gray-300"
				active="bg-green-200 border-b-2 border-green-500"
				name="active"
				value={3}>{m.active()}</Tab
			>
			<Tab
				bind:group={tabSet}
				class="border-x border-t border-gray-300"
				active="bg-red-300 border-b-2 border-red-600"
				name="deprecated"
				value={4}>{m.deprecated()}</Tab
			>
			<Tab
				bind:group={tabSet}
				class="border-x border-t border-gray-300"
				active="bg-gray-300 border-b-2 border-gray-600"
				name="noStatus"
				value={5}>{m.noStatus()}</Tab
			>
			<svelte:fragment slot="panel">
				<div class="p-2">
					{#if tabSet === 0}
						<ModelTable
							URLModel="applied-controls"
							source={toDoAppliedControls}
							search={true}
							rowsPerPage={true}
							orderBy={{ identifier: 'eta', direction: 'desc' }}
							tags={false}
						/>
					{/if}
					{#if tabSet === 1}
						<ModelTable
							URLModel="applied-controls"
							source={inProgressAppliedControls}
							search={true}
							rowsPerPage={true}
							orderBy={{ identifier: 'eta', direction: 'desc' }}
							tags={false}
						/>
					{/if}
					{#if tabSet === 2}
						<ModelTable
							URLModel="applied-controls"
							source={onHoldAppliedControls}
							search={true}
							rowsPerPage={true}
							orderBy={{ identifier: 'eta', direction: 'desc' }}
							tags={false}
						/>
					{/if}
					{#if tabSet === 3}
						<ModelTable
							URLModel="applied-controls"
							source={activeAppliedControls}
							search={true}
							rowsPerPage={true}
							orderBy={{ identifier: 'eta', direction: 'desc' }}
							tags={false}
						/>
					{/if}
					{#if tabSet === 4}
						<ModelTable
							URLModel="applied-controls"
							source={deprecatedAppliedControls}
							search={true}
							rowsPerPage={true}
							orderBy={{ identifier: 'eta', direction: 'desc' }}
							tags={false}
						/>
					{/if}
					{#if tabSet === 5}
						<ModelTable
							URLModel="applied-controls"
							source={noneAppliedControls}
							search={true}
							rowsPerPage={true}
							orderBy={{ identifier: 'eta', direction: 'desc' }}
							tags={false}
						/>
					{/if}
				</div>
			</svelte:fragment>
		</TabGroup>
	</div>
</div>
