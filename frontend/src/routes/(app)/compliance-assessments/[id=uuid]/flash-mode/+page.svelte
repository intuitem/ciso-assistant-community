<script lang="ts">
	import { page } from '$app/stores';
	import { id } from '$paraglide/messages';
	import type { PageData } from './$types';
	import { RadioGroup, RadioItem } from '@skeletonlabs/skeleton';

	export let data: PageData;
	const tree = data.tree;

	let possible_states = [
		'To do',
		'In progress',
		'Non Compliant',
		'Partially Compliant',
		'Compliant',
		'Not Applicable'
	];

	let expected_data = [
		{ status: 'To do', urn: 'xyz', requirement: 'This is a security requirement 1', id: '1' },
		{ status: 'In progress', urn: 'abc', requirement: 'This is a security requirement 2', id: '2' },
		{
			status: 'Non Compliant',
			urn: 'def',
			requirement: 'This is a security requirement 3',
			id: '3'
		},
		{
			status: 'Partially Compliant',
			urn: 'ghi',
			requirement: 'This is a security requirement 4',
			id: '4'
		},
		{ status: 'Compliant', urn: 'jkl', requirement: 'This is a security requirement 5', id: '5' },
		{
			status: 'Not Applicable',
			urn: 'mno',
			requirement: 'This is a security requirement 6',
			id: '6'
		}
	];

	// Reactive variable to keep track of the current item index
	let currentIndex = 0;

	// Function to handle the "Next" button click
	function nextItem() {
		if (currentIndex < expected_data.length - 1) {
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
		expected_data[currentIndex].status = event.target.value;
	}
</script>

<main class="p-20 flex justify-center items-center h-screen">
	<div class="bg-white w-1/2 h-1/2 rounded-xl shadow-xl p-4">
		{#if expected_data && expected_data.length > 0}
			{#if expected_data[currentIndex]}
				<div class="text-sm mt-4">{expected_data[currentIndex].urn}</div>
				<div class="mt-4 font-semibold">{currentIndex + 1}/{expected_data.length}</div>
				<div class="mt-4 text-lg">{expected_data[currentIndex].requirement}</div>
				<div class="mt-4 items-center">
					<div class="flex flex-row justify-between" />

					<div class="">
						<h3 class="mb-4 font-semibold text-gray-900 dark:text-white">status</h3>
						<ul
							class="items-center w-full text-sm font-medium text-gray-900 bg-white border border-gray-200 rounded-lg sm:flex dark:bg-gray-700 dark:border-gray-600 dark:text-white"
						>
							<li
								class="w-full border-b border-gray-200 sm:border-b-0 sm:border-r dark:border-gray-600"
							>
								<div class="flex items-center ps-3">
									<input
										id="horizontal-list-radio-license"
										type="radio"
										value=""
										name="list-radio"
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-700 dark:focus:ring-offset-gray-700 focus:ring-2 dark:bg-gray-600 dark:border-gray-500"
									/>
									<label
										for="horizontal-list-radio-license"
										class="w-full py-3 ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
										>Driver License
									</label>
								</div>
							</li>
							<li
								class="w-full border-b border-gray-200 sm:border-b-0 sm:border-r dark:border-gray-600"
							>
								<div class="flex items-center ps-3">
									<input
										id="horizontal-list-radio-id"
										type="radio"
										value=""
										name="list-radio"
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-700 dark:focus:ring-offset-gray-700 focus:ring-2 dark:bg-gray-600 dark:border-gray-500"
									/>
									<label
										for="horizontal-list-radio-id"
										class="w-full py-3 ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
										>State ID</label
									>
								</div>
							</li>
							<li
								class="w-full border-b border-gray-200 sm:border-b-0 sm:border-r dark:border-gray-600"
							>
								<div class="flex items-center ps-3">
									<input
										id="horizontal-list-radio-military"
										type="radio"
										value=""
										name="list-radio"
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-700 dark:focus:ring-offset-gray-700 focus:ring-2 dark:bg-gray-600 dark:border-gray-500"
									/>
									<label
										for="horizontal-list-radio-military"
										class="w-full py-3 ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
										>US Military</label
									>
								</div>
							</li>
							<li class="w-full dark:border-gray-600">
								<div class="flex items-center ps-3">
									<input
										id="horizontal-list-radio-passport"
										type="radio"
										value=""
										name="list-radio"
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-700 dark:focus:ring-offset-gray-700 focus:ring-2 dark:bg-gray-600 dark:border-gray-500"
									/>
									<label
										for="horizontal-list-radio-passport"
										class="w-full py-3 ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
										>US Passport</label
									>
								</div>
							</li>
                            <li class="w-full dark:border-gray-600">
								<div class="flex items-center ps-3">
									<input
										id="horizontal-list-bla1"
										type="radio"
										value=""
										name="list-radio"
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-700 dark:focus:ring-offset-gray-700 focus:ring-2 dark:bg-gray-600 dark:border-gray-500"
									/>
									<label
										for="horizontal-list-bla1"
										class="w-full py-3 ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
										>US Passport</label
									>
								</div>
							</li>
                            <li class="w-full dark:border-gray-600">
								<div class="flex items-center ps-3">
									<input
										id="horizontal-list-bla2"
										type="radio"
										value=""
										name="list-radio"
										class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-700 dark:focus:ring-offset-gray-700 focus:ring-2 dark:bg-gray-600 dark:border-gray-500"
									/>
									<label
										for="horizontal-list-bla2"
										class="w-full py-3 ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
										>US Passport</label
									>
								</div>
							</li>
						</ul>
					</div>

					<div class="mt-4 flex justify-between">
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
							disabled={currentIndex === expected_data.length - 1}
						>
							Next
						</button>
					</div>
				</div>
			{/if}
		{/if}
	</div>
</main>
