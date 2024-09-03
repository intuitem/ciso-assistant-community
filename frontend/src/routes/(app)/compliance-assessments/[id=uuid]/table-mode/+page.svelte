<script lang="ts">
	import type { PageData } from './$types';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';
	import { breadcrumbObject } from '$lib/utils/stores';
	import { complianceResultColorMap } from '$lib/utils/constants';

	export let data: PageData;

	let currentIndex = 0;
	$: currentRequirementAssessment = data.requirement_assessments[currentIndex];

	breadcrumbObject.set(data.compliance_assessment);

	const result_options = [
		{ id: 'not_assessed', label: m.notAssessed() },
		{ id: 'non_compliant', label: m.nonCompliant() },
		{ id: 'partially_compliant', label: m.partiallyCompliant() },
		{ id: 'compliant', label: m.compliant() },
		{ id: 'not_applicable', label: m.notApplicable() }
	];
	const status_options = [
		{ id: 'to_do', label: m.toDo() },
		{ id: 'in_progress', label: m.inProgress() },
		{ id: 'in_review', label: m.inReview() },
		{ id: 'done', label: m.done() }
	];

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement) => [requirement.id, requirement])
	);

	function title(requirementAssessment) {
		const requirement = requirementHashmap[requirementAssessment.requirement];
		const parent = data.requirements.find((req) => req.urn === requirement.parent_urn);
		return requirement.display_short
			? requirement.display_short
			: parent.display_short
				? parent.display_short
				: parent.description;
	}

	// Function to update requirement assessments
	function update(event, requirementAssessment, field: string) {
		requirementAssessment[field] = event.target.value;
		const form = document.getElementById(`tableModeForm-${requirementAssessment.id}`);
		const formData = {
			id: requirementAssessment.id,
			[field]: event.target.value
		};
		fetch(form.action, {
			method: 'POST',
			body: JSON.stringify(formData)
		});
	}
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div
		class="card px-6 py-4 bg-white flex flex-col justify-between shadow-lg w-full h-full space-y-2"
	>
		{#each data.requirement_assessments as requirementAssessment}
			<div
				class="flex flex-col items-center justify-center border pb-2 px-2 shadow-lg rounded-md space-y-2"
			>
				<h1 class="font-semibold text-xl">{title(requirementAssessment)}</h1>
				<div class="flex flex-col space-x-2 items-center justify-evenly w-full">
					<form
						class="flex flex-row w-full space-x-2"
						id="tableModeForm-{requirementAssessment.id}"
						action="?/updateRequirementAssessment"
						method="post"
					>
						<div class="flex flex-col items-center w-1/2">
							<p class="flex items-center font-semibold">Status</p>
							<RadioGroup class="w-full flex-wrap items-center">
								{#each status_options as option}
									<RadioItem
										class="h-full"
										id={option.id}
										value={option.id}
										bind:group={requirementAssessment.status}
										name="status"
										on:change={(event) => update(event, requirementAssessment, 'status')}
										>{option.label}</RadioItem
									>
								{/each}
							</RadioGroup>
						</div>
						<div class="flex flex-col items-center w-1/2">
							<p class="flex items-center font-semibold">Result</p>
							<RadioGroup class="w-full flex-wrap items-center">
								{#each result_options as option}
									<RadioItem
										class="h-full"
										id={option.id}
										value={option.id}
										bind:group={requirementAssessment.result}
										name="result"
										on:change={(event) => update(event, requirementAssessment, 'result')}
										>{option.label}</RadioItem
									>
								{/each}
							</RadioGroup>
						</div>
					</form>
				</div>
				<div class="flex flex-col w-full">
					{#if Object.keys(requirementAssessment.answer).length !== 0}
						<p class="flex items-center font-semibold">Question</p>
						{#each requirementAssessment.answer.questions as question}
							<li class="flex justify-between items-center border rounded-xl p-2 disabled">
								{question.text}
								<p class="text-sm font-semibold text-primary-500">
									{#if question.answer}
										{question.answer}
									{:else}
										{m.undefined()}
									{/if}
								</p>
							</li>
						{/each}
					{/if}
				</div>
			</div>
		{/each}
	</div>
</div>
