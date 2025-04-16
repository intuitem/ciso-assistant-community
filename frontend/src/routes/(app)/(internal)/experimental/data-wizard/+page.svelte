<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';
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
			title: 'Caution',
			body: 'The following will create multiple objects in batch mode and possibly on different domains. This operation cannot be undone and you will need to do the clean up in case of an issue.',
			response: (r: boolean) => {
				if (r) formElement.requestSubmit();
			}
		};

		if (file) modalStore.trigger(modal);
	}

	// Determine if domain selection should be disabled
	$: isDomainDisabled =
		selectedModel === 'ComplianceAssessment' || selectedModel === 'FindingsAssessment';

	$: isFrameworkDisabled = selectedModel !== 'ComplianceAssessment';

	// Determine if perimeter selection should be disabled
	$: isPerimeterDisabled =
		selectedModel === 'Asset' ||
		selectedModel === 'AppliedControl' ||
		selectedModel === 'Perimeter';

	$: uploadButtonStyles = file ? '' : 'chip-disabled';

	// Helper to check if the form has been processed (form action has run)
	$: formSubmitted = form !== null && form !== undefined;

	const authorizedExtensions = ['.xls', '.xlsx'];
</script>

<div class="grid grid-cols-4 gap-4">
	<div class=" col-span-2 bg-white shadow py-4 px-6 space-y-2">
		<form enctype="multipart/form-data" method="post" use:enhance bind:this={formElement}>
			<div>
				<h4 class="h4 font-bold"><i class="fa-solid fa-file-excel mr-2" />Load excel data</h4>
				<a
					class="text-indigo-600 hover:text-indigo-400"
					href="https://intuitem.gitbook.io/ciso-assistant/guide/data-import-wizard"
					>Templates and guidelines</a
				>
			</div>
			<div class=" py-4">
				<ol class="list-decimal list-inside">
					<li>Select your file and make sure it matches the templates</li>
					<li>Choose the corresponding model</li>
					<li>Select the scope</li>
					<li>Click Upload</li>
				</ol>
			</div>
			<input
				id="file"
				type="file"
				name="file"
				accept={authorizedExtensions.join(',')}
				required
				bind:value={file}
			/>

			<div class="rounded-lg p-4 mt-4 border-green-500 border-2">
				<!--Model radio-->
				<fieldset class="space-y-4">
					<legend class="sr-only">Object</legend>

					<div>
						<label
							for="Asset"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-xs hover:border-gray-200 has-[:checked]:border-blue-500 has-[:checked]:ring-1 has-[:checked]:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.assets()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="Asset"
								id="Asset"
								class="size-5 border-gray-300 text-blue-500"
								checked
								bind:group={selectedModel}
							/>
						</label>
					</div>

					<div>
						<label
							for="AppliedControl"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-xs hover:border-gray-200 has-[:checked]:border-blue-500 has-[:checked]:ring-1 has-[:checked]:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.appliedControls()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="AppliedControl"
								id="AppliedControl"
								class="size-5 border-gray-300 text-blue-500"
								bind:group={selectedModel}
							/>
						</label>
					</div>

					<div>
						<label
							for="Perimeter"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-xs hover:border-gray-200 has-[:checked]:border-blue-500 has-[:checked]:ring-1 has-[:checked]:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.perimeters()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="Perimeter"
								id="Perimeter"
								class="size-5 border-gray-300 text-blue-500"
								bind:group={selectedModel}
							/>
						</label>
					</div>

					<div>
						<label
							for="ComplianceAssessment"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-xs hover:border-gray-200 has-[:checked]:border-blue-500 has-[:checked]:ring-1 has-[:checked]:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.complianceAssessment()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="ComplianceAssessment"
								id="ComplianceAssessment"
								class="size-5 border-gray-300 text-blue-500"
								bind:group={selectedModel}
							/>
						</label>
					</div>

					<div>
						<label
							for="FindingsAssessment"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-xs hover:border-gray-200 has-[:checked]:border-blue-500 has-[:checked]:ring-1 has-[:checked]:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.findingsAssessment()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="FindingsAssessment"
								id="FindingsAssessment"
								class="size-5 border-gray-300 text-blue-500"
								bind:group={selectedModel}
							/>
						</label>
					</div>
				</fieldset>
			</div>

			<div class="rounded-lg p-4 mt-4 border-pink-500 border-2">
				<!--Select targets -->
				<label for="folder" class="block text-sm font-medium text-gray-900"
					>Select a fallback Domain (if not set on the file)</label
				>
				<select
					id="folder"
					name="folder"
					disabled={isDomainDisabled}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
				>
					{#each data.data.folders as folder}
						<option value={folder.id}>{folder.name}</option>
					{/each}
				</select>
				<label for="perimeter" class="block text-sm font-medium text-gray-900"
					>Select a Perimeter</label
				>
				<select
					id="perimeter"
					name="perimeter"
					disabled={isPerimeterDisabled}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
				>
					{#each data.data.perimeters as perimeter}
						<option value={perimeter.id}>{perimeter.name}</option>
					{/each}
				</select>

				<label for="framework" class="block text-sm font-medium text-gray-900"
					>Select a Framework</label
				>
				<select
					id="framework"
					name="framework"
					disabled={isFrameworkDisabled}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
				>
					{#each data.data.frameworks as framework}
						<option value={framework.id}>{framework.name}</option>
					{/each}
				</select>
			</div>
			<div class="flex py-4">
				<button
					class="btn variant-filled mt-2 lg:mt-0 {uploadButtonStyles}"
					type="button"
					on:click={modalConfirm}><i class="fa-solid fa-file-arrow-up mr-2"></i>{m.upload()}</button
				>
			</div>
		</form>
	</div>
	<div class="col-span-2 p-4">
		Parsing results:
		{#if formSubmitted}
			<div class="col-span-full mb-4">
				{#if form?.success}
					<div class="alert alert-success variant-filled-success">
						<div>{form.message || 'File uploaded successfully'}</div>
					</div>
					<div class="text-xs font-mono p-2">{JSON.stringify(form?.results, null, 2)}</div>
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
						<p>{JSON.stringify(form?.results, null, 2)}</p>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
