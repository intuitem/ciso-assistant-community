<script lang="ts">
	import type { PageData } from './$types';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';
	import { breadcrumbObject } from '$lib/utils/stores';

	export let data: PageData;

	breadcrumbObject.set(data.compliance_assessment);

	let possible_options = [
		{ id: 'to_do', label: 'To do' },
		{ id: 'in_progress', label: 'In progress' },
		{ id: 'non_compliant', label: 'Non Compliant' },
		{ id: 'partially_compliant', label: 'Partially Compliant' },
		{ id: 'compliant', label: 'Compliant' },
		{ id: 'not_applicable', label: 'Not Applicable' }
	];

	// Reactive variable to keep track of the current item index
	let currentIndex = 0;

	// Function to handle the "Next" button click
	function nextItem() {
		if (currentIndex < data.requirement_assessments.length - 1) {
			currentIndex += 1;
		}
	}

	// Function to handle the "Back" button click
	function previousItem() {
		if (currentIndex > 0) {
			currentIndex -= 1;
		}
	}

	// Function to update the status of the current item
	function updateStatus(event) {
		data.requirement_assessments[currentIndex].status = event.target.value;
        console.log("we can perform the api call here to update the status of item ", data.requirement_assessments[currentIndex].id, " to ", event.target.value);
		const form = document.getElementById('flashModeForm');
		const formData = new FormData(form);
		fetch(form.action, {
			method: 'POST',
			body: formData
		})
	}
</script>

<div class="flex h-full justify-center items-center">
	<div class="flex flex-col bg-white w-1/2 h-1/2 rounded-xl shadow-xl p-4">
		{#if data.requirement_assessments[currentIndex]}
			<div class="flex flex-col w-full h-full space-y-4">
				<div class="flex justify-between">
					<div class="text-sm mt-4">{data.requirement_assessments[currentIndex].name}</div>
					<div class="mt-4 font-semibold">{currentIndex + 1}/{data.requirement_assessments.length}</div>
				</div>
				<div class="flex text-lg h-1/3 items-center">{data.requirement_assessments[currentIndex].description}</div>
				<div class="items-center">
					<div class="">
						<h3 class="mb-4 font-semibold text-gray-900 dark:text-white">Status</h3>
						<form id="flashModeForm" action="?/updateRequirementAssessment" method="post">
						<ul
							class="items-center w-full text-sm font-medium text-gray-900 bg-white border border-gray-200 rounded-lg sm:flex dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						>
							<input hidden name="id" value={data.requirement_assessments[currentIndex].id}/>
							{#each possible_options as option}
								<li
									class="w-full border-b border-gray-200 sm:border-b-0 sm:border-r dark:border-gray-600"
								>
									<div class="flex items-center ps-3">	
											<input
											id={option.id}
											type="radio"
											value={option.id}
											name="status"
											checked={option.id === data.requirement_assessments[currentIndex].status}
											on:change={updateStatus}
											class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-700 dark:focus:ring-offset-gray-700 focus:ring-2 dark:bg-gray-600 dark:border-gray-500"
											/>
										<label
											for={option.id}
											class="w-full py-3 ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
											>{option.label}
										</label>
									</div>
								</li>
							{/each}
						</ul>
						</form>
					</div>
				</div>
			</div>
			<div class="flex justify-between">
				<button
					class="bg-gray-500 text-white px-4 py-2 rounded"
					on:click={previousItem}
					disabled={currentIndex === 0}
				>
					Back
				</button>
				<button
					class="bg-blue-500 text-white px-4 py-2 rounded"
					on:click={nextItem}
					disabled={currentIndex === data.requirement_assessments.length - 1}
				>
					Next
				</button>
			</div>
		{/if}
	</div>
</div>

