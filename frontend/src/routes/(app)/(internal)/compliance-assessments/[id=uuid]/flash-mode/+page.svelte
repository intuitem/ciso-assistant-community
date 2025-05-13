<script lang="ts">
	import { complianceResultTailwindColorMap } from '$lib/utils/constants';
	import { m } from '$paraglide/messages';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const possible_options = [
		{ id: 'not_assessed', label: m.notAssessed() },
		{ id: 'non_compliant', label: m.nonCompliant() },
		{ id: 'partially_compliant', label: m.partiallyCompliant() },
		{ id: 'compliant', label: m.compliant() },
		{ id: 'not_applicable', label: m.notApplicable() }
	];

	// Reactive variable to keep track of the current item index
	const requirementAssessments = data.requirement_assessments.filter(
		(requirement) => requirement.name || requirement.description
	);
	let currentIndex = $state(0);
	let currentRequirementAssessment = $derived(requirementAssessments[currentIndex]);

	let color = $derived(complianceResultTailwindColorMap[currentRequirementAssessment.result]);

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement) => [requirement.id, requirement])
	);
	let requirement = $derived(requirementHashmap[currentRequirementAssessment.requirement.id]);
	let parent = $derived(data.requirements.find((req) => req.urn === requirement.parent_urn));

	let title = $derived(requirement.display_short
		? requirement.display_short
		: parent.display_short
			? parent.display_short
			: parent.description);

	// Function to handle the "Next" button click
	function nextItem() {
		if (currentIndex < requirementAssessments.length - 1) {
			currentIndex += 1;
		} else {
			currentIndex = 0;
		}
	}

	// Function to handle the "Back" button click
	function previousItem() {
		if (currentIndex > 0) {
			currentIndex -= 1;
		} else {
			currentIndex = requirementAssessments.length - 1;
		}
	}

	let result = $derived(currentRequirementAssessment.result);

	// Function to update the result of the current item
	function updateResult(newResult: string | null) {
		currentRequirementAssessment.result = newResult;
		const form = document.getElementById('flashModeForm');
		const formData = {
			id: currentRequirementAssessment.id,
			result: newResult
		};
		fetch(form.action, {
			method: 'POST',
			body: JSON.stringify(formData)
		});
	}
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'n' || event.key === 'l') {
			nextItem();
		} else if (event.key === 'p' || event.key === 'h') {
			previousItem();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />
<div class="flex flex-col h-full justify-center items-center">
	<div
		style="border-color: {color}"
		class="flex flex-col bg-white w-3/4 h-3/4 rounded-xl shadow-xl p-4 border-4"
	>
		{#if currentRequirementAssessment}
			<div class="flex flex-col w-full h-full space-y-4">
				<div class="flex justify-between">
					<div class="">
						<a
							href="/compliance-assessments/{data.compliance_assessment.id}"
							class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
						>
							<i class="fa-solid fa-arrow-left"></i>
							<p class="">{m.goBackToAudit()}</p>
						</a>
					</div>
					<div class="font-semibold">{currentIndex + 1}/{requirementAssessments.length}</div>
				</div>
				<div class="flex flex-col items-center text-center justify-center">
					<p class="font-semibold">{title}</p>
				</div>
				<div class="flex flex-col items-center justify-center whitespace-pre-wrap leading-relaxed">
					{#if currentRequirementAssessment.description}
						{currentRequirementAssessment.description}
					{/if}
				</div>
			</div>
			<div class="items-center my-4">
				<div>
					<form id="flashModeForm" action="?/updateRequirementAssessment" method="post">
						<ul
							class=" items-center w-full text-sm font-medium text-gray-900 bg-white border border-gray-200 rounded-lg sm:flex dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						>
							<RadioGroup class="w-full flex-wrap items-center">
								{#each possible_options as option}
									<RadioItem
										class="h-full"
										active={color}
										id={option.id}
										value={option.id}
										bind:group={result}
										name="result"
										style="border-color: {color}"
										on:click={() => {
											const newResult = result === option.id ? 'not_assessed' : option.id;
											updateResult(newResult);
										}}
									>
										{option.label}
									</RadioItem>
								{/each}
							</RadioGroup>
						</ul>
					</form>
				</div>
			</div>
			<div class="flex justify-between">
				<button class="bg-gray-400 text-white px-4 py-2 rounded" onclick={previousItem}>
					{m.previous()}
				</button>
				<button class="variant-filled-primary px-4 py-2 rounded" onclick={nextItem}>
					{m.next()}
				</button>
			</div>
		{/if}
	</div>
</div>
