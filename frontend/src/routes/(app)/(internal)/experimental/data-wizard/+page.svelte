<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages';
	import type { PageData } from './$types';

	export let data: PageData;
	export let form;

	import type { ModalSettings, ModalComponent, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';

	const modalStore: ModalStore = getModalStore();

	let formElement: HTMLFormElement;
	let file: HTMLInputElement;
	let selectedModel = 'Asset'; // Default selection

	function modalConfirm(): void {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal
		};

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: 'Data import',
			body: 'The following will create objects in batch mode and cannot be undone...',
			response: (r: boolean) => {
				if (r) formElement.requestSubmit();
			}
		};

		if (file) modalStore.trigger(modal);
	}

	// Determine if domain selection should be disabled
	$: isDomainDisabled = selectedModel === 'ComplianceAssessment';

	// Determine if perimeter selection should be disabled
	$: isPerimeterDisabled = selectedModel === 'Asset' || selectedModel === 'AppliedControl';

	$: uploadButtonStyles = file ? '' : 'chip-disabled';

	// Helper to check if the form has been processed (form action has run)
	$: formSubmitted = form !== null && form !== undefined;

	const authorizedExtensions = ['.xls', '.xlsx'];
</script>

<div class="grid grid-cols-2 space-y-2 p-2">
	<form enctype="multipart/form-data" method="post" use:enhance bind:this={formElement}>
		<div class="card col-span-full lg:col-span-1 bg-white shadow py-4 px-6 space-y-2">
			<h4 class="h4 font-semibold">Load excel data <i class="fa-solid fa-upload" /></h4>
			<div class=" py-4">
				Choose the type of data you are importing. Check out the templates on the side
			</div>
			<input
				id="file"
				type="file"
				name="file"
				accept={authorizedExtensions.join(',')}
				required
				bind:value={file}
			/>
			<div class="p-4 border">
				<div class="flex items-center mb-4">
					<input
						checked
						id="Asset"
						type="radio"
						value="Asset"
						name="model"
						bind:group={selectedModel}
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
					/>
					<label for="Asset" class="ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
						>{m.assets()}</label
					>
				</div>
				<div class="flex items-center mb-4">
					<input
						id="AppliedControl"
						type="radio"
						value="AppliedControl"
						name="model"
						bind:group={selectedModel}
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
					/>
					<label
						for="AppliedControl"
						class="ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
						>{m.appliedControls()}</label
					>
				</div>
				<div class="flex items-center">
					<input
						id="ComplianceAssessment"
						type="radio"
						value="ComplianceAssessment"
						name="model"
						bind:group={selectedModel}
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
					/>
					<label
						for="ComplianceAssessment"
						class="ms-2 text-sm font-medium text-gray-900 dark:text-gray-300"
						>{m.complianceAssessment()}</label
					>
				</div>
			</div>

			<label for="folder" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
				>Select a Domain</label
			>
			<select
				id="folder"
				name="folder"
				disabled={isDomainDisabled}
				class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
			>
				{#each data.data.folders as folder}
					<option value={folder.id}>{folder.name}</option>
				{/each}
			</select>
			<label for="perimeter" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
				>Select a Perimeter</label
			>
			<select
				id="perimeter"
				name="perimeter"
				disabled={isPerimeterDisabled}
				class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
			>
				{#each data.data.perimeters as perimeter}
					<option value={perimeter.id}>{perimeter.name}</option>
				{/each}
			</select>

			<button
				class="btn variant-filled mt-2 lg:mt-0 {uploadButtonStyles}"
				type="button"
				on:click={modalConfirm}>{m.upload()}</button
			>
		</div>
	</form>
</div>
<div>
	Parsing results:
	{#if formSubmitted}
		<div class="col-span-full mb-4">
			{#if form?.success}
				<div class="alert alert-success variant-filled-success">
					<p>{form.message || 'File uploaded successfully'}</p>
				</div>
			{:else}
				<div class="alert alert-error variant-filled-error">
					<p>
						{form?.error
							? typeof m[form.error] === 'function'
								? m[form.error]()
								: form.error
							: 'An error occurred'}
					</p>
					<p>{form?.message}</p>
				</div>
			{/if}
		</div>
	{/if}
</div>
