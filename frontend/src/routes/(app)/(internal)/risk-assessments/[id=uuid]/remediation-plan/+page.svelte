<script lang="ts">
	import * as m from '$paraglide/messages.js';
	import { breadcrumbObject } from '$lib/utils/stores';
	import { safeTranslate } from '$lib/utils/i18n.js';
	import { toCamelCase } from '$lib/utils/locales.js';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';

	export let data;

	breadcrumbObject.set(data.risk_assessment);

	const scenarioTreatmentColorMap = (status: string) => {
		const map: Record<string, string> = {
			open: 'bg-orange-200',
			mitigate: 'bg-green-200',
			accept: 'bg-sky-200',
			avoid: 'bg-red-200',
			transfer: 'bg-violet-200'
		};
		return map[status] ?? 'bg-gray-200';
	};

	const APPLIED_CONTROL_FIELDS = [
		'name',
		'description',
		'category',
		'csf_function',
		'reference_control',
		'eta',
		'effort',
		'cost',
		'link',
		'status'
	];
	function makeSourceFromAppliedControls(appliedControls): TableSource {
		const fields = APPLIED_CONTROL_FIELDS;
		const head = Object.fromEntries(fields.map((field) => [field, toCamelCase(field)]));

		return {
			head: head,
			body: appliedControls.map((appliedControl) =>
				Object.fromEntries(fields.map((field) => [field, appliedControl[field]]))
			),
			meta: appliedControls
		};
	}
</script>

<div class="bg-white p-2 m-2 shadow rounded-lg space-x-2 flex flex-row justify-center">
	<p class="font-semibold text-lg">
		{m.project()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/projects/{data.risk_assessment.project.id}/">{data.risk_assessment.project.str}</a
		>
	</p>
	<p>/</p>
	<p class="font-semibold text-lg">
		{m.riskAssessment()}:
		<a
			class="unstyled text-primary-500 hover:text-primary-700 cursor-pointer"
			href="/risk-assessments/{data.risk_assessment.id}/"
			>{data.risk_assessment.name} - {data.risk_assessment.version}</a
		>
	</p>
</div>

<p class="p-2 m-2 text-lg font-semibold">{m.associatedRiskScenarios()}:</p>

<div class="bg-white p-2 m-2 shadow overflow-hidden rounded-lg flex flex-col">
	{#each data.risk_assessment.risk_scenarios as scenario}
		<tr class="bg-gray-100">
			<td class="text-lg p-3" colspan="9">
				<a
					class="unstyled text-primary-500 hover:text-primary-700"
					href="/risk-scenarios/{scenario.id}">{scenario.name}</a
				>
				<span class="badge {scenarioTreatmentColorMap(scenario.treatment)}"
					>{safeTranslate(scenario.treatment)}</span
				>
			</td>
		</tr>
		{#if scenario.existing_controls}
			<tr>
				<td class="text-md pl-6 pb-3 font-medium" colspan="9"> {m.existingControls()}: </td>
			</tr>
			<tr>
				<td class="text-sm pl-6 pb-3" colspan="9"> {scenario.existing_controls} </td>
			</tr>
		{/if}
		{#if scenario.applied_controls.length > 0}
			<ModelTable
				source={makeSourceFromAppliedControls(scenario.applied_controls)}
				URLModel="applied-controls"
			/>
		{/if}
		{#if !scenario.existing_controls && !(scenario.applied_controls.length > 0)}
			<tr>
				<td colspan="9" class="p-2 text-left">
					<i class="fas fa-exclamation-circle" />
					{m.noAppliedControlYet()}
				</td>
			</tr>
		{/if}
	{/each}
</div>
