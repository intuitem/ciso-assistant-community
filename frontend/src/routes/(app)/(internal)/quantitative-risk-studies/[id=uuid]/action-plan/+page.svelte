<script lang="ts">
	import { page } from '$app/state';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';

	let { data } = $props();

	const modalStore = getModalStore();

	const appliedControlsHead = {
		name: 'name',
		status: 'status',
		priority: 'priority',
		category: 'category',
		effort: 'effort',
    annual_cost: 'cost',
    control_impact: "controlImpact",
		eta: 'eta',
		quantitative_risk_scenarios: 'scenarios'
	};

	const appliedControls: TableSource = {
		head: appliedControlsHead,
		body: [],
		meta: []
	};

$inspect(data);
</script>

<div class="bg-white p-2 shadow rounded-lg space-x-2 flex flex-row justify-center mb-2">
	<p class="font-semibold text-lg">
		{m.folder()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/folders/{data.quantitative_risk_study.folder.id}/"
			>{data.quantitative_risk_study.folder.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		Quantitative Risk Study:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/quantitative-risk-studies/{data.quantitative_risk_study.id}/"
			>{data.quantitative_risk_study.name}</a
		>
	</p>
</div>

<div class="flex flex-col space-y-4 bg-white p-4 shadow rounded-lg space-x-2">
	<div class="flex justify-between items-center">
		<div>
			<p class="text-xl font-extrabold">Action Plan</p>
			<p class="text-sm text-gray-500">
				Controls from quantitative risk hypotheses
			</p>
		</div>
	</div>

	<div class="">
		<ModelTable
			URLModel="applied-controls"
			source={appliedControls}
			search={true}
			rowsPerPage={true}
			orderBy={{ identifier: 'eta', direction: 'desc' }}
			baseEndpoint="/quantitative-risk-studies/{page.params.id}/action-plan"
			fields={[
				'name',
				'status',
				'priority',
				'category',
				'effort',
        'annual_cost',
        'control_impact',
				'eta',
				'quantitative_risk_scenarios'
			]}
		/>
	</div>
</div>

<!-- Modal component for problematic scenarios -->
<!-- This would be registered as a modal component in your app -->
