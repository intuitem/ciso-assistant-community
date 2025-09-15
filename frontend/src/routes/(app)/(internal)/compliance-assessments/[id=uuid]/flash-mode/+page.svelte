<script lang="ts">
	import { complianceResultTailwindColorMap } from '$lib/utils/constants';
	import RadioGroup from '$lib/components/Forms/RadioGroup.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

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

	let title = $derived(
		requirement.display_short
			? requirement.display_short
			: parent.display_short
				? parent.display_short
				: parent.description
	);

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

	// svelte-ignore state_referenced_locally
	let result = $state(currentRequirementAssessment.result);
	$effect(() => {
		result = currentRequirementAssessment.result;
	});

	// Function to update the result of the current item
	function updateResult(newResult: string | null) {
		currentRequirementAssessment.result = newResult;
		result = newResult;
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

	// Navigation state
	let showNavigation = $state(false);
	let jumpToInput = $state('');

	function jumpToItem(index: number) {
		if (index >= 0 && index < requirementAssessments.length) {
			currentIndex = index;
			showNavigation = false;
			jumpToInput = '';
		}
	}

	function handleJumpSubmit() {
		const targetIndex = parseInt(jumpToInput) - 1; // Convert to 0-based index
		jumpToItem(targetIndex);
	}

	function handleKeydown(event: KeyboardEvent) {
		const key = event.key.toLowerCase();
		const target = event.target as HTMLElement | null;
		const tag = target?.tagName?.toLowerCase();
		const isEditable = target?.isContentEditable;
		if (
			(tag === 'input' || tag === 'textarea' || tag === 'select' || isEditable) &&
			target?.id !== 'jumpInput'
		) {
			return;
		}
		if (key === 'n' || key === 'l') {
			event.preventDefault();
			nextItem();
		} else if (key === 'p' || key === 'h') {
			event.preventDefault();
			previousItem();
		} else if (event.key === 'g') {
			showNavigation = !showNavigation;
			if (showNavigation) {
				setTimeout(() => {
					document.getElementById('jumpInput')?.focus();
				}, 0);
			}
		} else if (key === 'escape') {
			showNavigation = false;
			jumpToInput = '';
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />
<div class="flex flex-col min-h-screen justify-center items-center">
	<div
		style="border-color: {color}"
		class="flex flex-col bg-white w-3/4 max-w-4xl h-3/4 min-h-[600px] rounded-xl shadow-xl p-4 border-4"
	>
		{#if currentRequirementAssessment}
			<!-- Header -->
			<div class="flex justify-between items-center">
				<div class="">
					<a
						href="/compliance-assessments/{data.compliance_assessment.id}"
						class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
					>
						<i class="fa-solid fa-arrow-left"></i>
						<p class="">{m.goBackToAudit()}</p>
					</a>
				</div>
				<div class="relative">
					<button
						class="font-semibold hover:bg-gray-100 px-2 py-1 rounded cursor-pointer border border-transparent hover:border-gray-300 transition-colors flex items-center space-x-1"
						onclick={() => (showNavigation = !showNavigation)}
						title="Click to jump to specific item (or press G)"
					>
						<span>{currentIndex + 1}/{requirementAssessments.length}</span>
						<i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
						<span class="text-xs opacity-60">(G)</span>
					</button>

					{#if showNavigation}
						<div
							class="absolute top-full right-0 mt-2 bg-white border border-gray-300 rounded-lg shadow-lg p-4 z-10 min-w-64"
						>
							<div class="flex flex-col space-y-3">
								<div class="text-sm font-medium">Jump to item:</div>
								<div class="flex space-x-2">
									<input
										id="jumpInput"
										bind:value={jumpToInput}
										type="number"
										min="1"
										max={requirementAssessments.length}
										placeholder="Item number"
										class="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
										onkeydown={(e) => {
											if (e.key === 'Enter') {
												e.preventDefault();
												handleJumpSubmit();
											}
										}}
									/>
									<button
										class="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
										onclick={handleJumpSubmit}
									>
										Go
									</button>
								</div>
								<div class="text-xs text-gray-500">
									Press G to toggle, Enter to jump, Esc to close
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Main content area -->
			<div class="flex flex-col flex-1 justify-center overflow-hidden">
				<div class="flex flex-col items-center text-center space-y-6 h-full">
					<p class="font-semibold text-xl flex-shrink-0">{title}</p>
					<div class="flex flex-col space-y-4 overflow-y-auto flex-1 w-full max-w-4xl px-4">
						{#if currentRequirementAssessment.description}
							<div class="whitespace-pre-wrap leading-relaxed text-gray-700">
								<MarkdownRenderer content={currentRequirementAssessment.description} />
							</div>
						{/if}
						{#if requirement.annotation}
							<div
								class="whitespace-pre-wrap leading-relaxed text-gray-600 italic bg-gray-50 p-4 rounded-lg border-l-4 border-blue-200 text-justify"
							>
								<MarkdownRenderer content={requirement.annotation} />
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Options and Navigation -->
			<div class="flex flex-col space-y-6">
				<div class="flex justify-center">
					<form id="flashModeForm" action="?/updateRequirementAssessment" method="post">
						<ul
							class="items-center w-full text-sm font-medium text-gray-900 bg-white rounded-lg sm:flex dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						>
							<RadioGroup
								possibleOptions={possible_options}
								initialValue={currentRequirementAssessment.result}
								classes="w-full"
								colorMap={complianceResultTailwindColorMap}
								field="result"
								onChange={(newValue) => {
									const newResult = result === newValue ? 'not_assessed' : newValue;
									updateResult(newResult);
								}}
								key="id"
								labelKey="label"
							/>
						</ul>
					</form>
				</div>

				<div class="flex justify-between">
					<button
						class="bg-gray-400 text-white px-4 py-2 rounded-sm flex items-center space-x-2"
						onclick={previousItem}
					>
						<span>{m.previous()}</span>
						<span class="text-xs opacity-75">(H)</span>
					</button>
					<button
						class="preset-filled-primary-500 px-4 py-2 rounded-sm flex items-center space-x-2"
						onclick={nextItem}
					>
						<span>{m.next()}</span>
						<span class="text-xs opacity-75">(L)</span>
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
