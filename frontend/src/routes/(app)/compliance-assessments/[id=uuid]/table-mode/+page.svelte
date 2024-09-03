<script lang="ts">
	import type { PageData } from './$types';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';
	import * as m from '$paraglide/messages';
	import { breadcrumbObject } from '$lib/utils/stores';
	import {
		complianceResultTailwindColorMap,
		complianceStatusTailwindColorMap
	} from '$lib/utils/constants';

	export let data: PageData;

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
	function update(event, requirementAssessment, field: string, question: string = '') {
		let value;
		if (question) {
			const questionIndex = requirementAssessment.answer.questions.findIndex(
				(q) => q.urn === question.urn
			);
			requirementAssessment.answer.questions[questionIndex].answer = event.target.value;
			value = requirementAssessment.answer;
		} else {
			requirementAssessment[field] = event.target.value;
			value = requirementAssessment[field];
		}
		const form = document.getElementById(`tableModeForm-${requirementAssessment.id}`);
		const formData = {
			id: requirementAssessment.id,
			[field]: value
		};
		fetch(form.action, {
			method: 'POST',
			body: JSON.stringify(formData)
		});
	}

	function addColor(result: string, map: Record<string, string>) {
		return map[result];
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
				<form
					class="flex flex-col space-x-2 items-center justify-evenly w-full"
					id="tableModeForm-{requirementAssessment.id}"
					action="?/updateRequirementAssessment"
					method="post"
				>
					<div class="flex flex-row w-full space-x-2">
						<div class="flex flex-col items-center w-1/2">
							<p class="flex items-center font-semibold">Status</p>
							<RadioGroup class="w-full flex-wrap items-center">
								{#each status_options as option}
									<RadioItem
										class="h-full"
										id={option.id}
										active={addColor(
											requirementAssessment.status,
											complianceStatusTailwindColorMap
										)}
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
										active={addColor(
											requirementAssessment.result,
											complianceResultTailwindColorMap
										)}
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
					</div>
					<div class="flex flex-col w-full">
						{#if Object.keys(requirementAssessment.answer).length !== 0}
							<p class="flex items-center font-semibold justify-center">Question</p>
							{#each requirementAssessment.answer.questions as question}
								<li class="flex justify-between items-center border rounded-xl p-2">
									{question.text}
									{#if question.type === 'unique_choice'}
										<RadioGroup active="variant-filled-primary" hover="hover:variant-soft-primary">
											{#each question.options as option}
												<RadioItem
													bind:group={question.answer}
													name="question"
													value={option}
													on:change={(event) =>
														update(event, requirementAssessment, 'answer', question)}
													>{option}</RadioItem
												>
											{/each}
										</RadioGroup>
									{:else if question.type === 'date'}
										<input type="date" placeholder="" class="w-fit" bind:value={question.answer} />
									{:else}
										<input type="text" placeholder="" class="w-fit" bind:value={question.answer} />
									{/if}
								</li>
							{/each}
						{/if}
					</div>
				</form>
			</div>
		{/each}
	</div>
</div>
