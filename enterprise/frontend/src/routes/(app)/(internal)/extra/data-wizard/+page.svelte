<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	interface Props {
		data: PageData;
		form: any;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	let formElement: HTMLFormElement = $state();
	let files: FileList | null = $state(null); // Fixed: Changed from HTMLInputElement to FileList
	let selectedModel = $state('Asset'); // Default selection

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

		// Fixed: Check for files instead of file
		if (files && files.length > 0) {
			modalStore.trigger(modal);
		}
	}

	// Determine if domain selection should be disabled
	let isDomainDisabled = $derived(
		selectedModel === 'ComplianceAssessment' ||
			selectedModel === 'FindingsAssessment' ||
			selectedModel === 'RiskAssessment'
	);

	let isFrameworkDisabled = $derived(selectedModel !== 'ComplianceAssessment');

	let isMatrixDisabled = $derived(selectedModel !== 'RiskAssessment');

	// Determine if perimeter selection should be disabled
	let isPerimeterDisabled = $derived(
		selectedModel === 'Asset' ||
			selectedModel === 'AppliedControl' ||
			selectedModel === 'Perimeter' ||
			selectedModel === 'ElementaryAction'
	);

	// Fixed: Check files correctly
	let uploadButtonStyles = $derived(files && files.length > 0 ? '' : 'chip-disabled');

	// Helper to check if the form has been processed (form action has run)
	let formSubmitted = $derived(form !== null && form !== undefined);

	const authorizedExtensions = ['.xls', '.xlsx'];
</script>

<div class="grid grid-cols-4 gap-4">
	<div class=" col-span-2 bg-white shadow-sm py-4 px-6 space-y-2">
		<form enctype="multipart/form-data" method="post" use:enhance bind:this={formElement}>
			<div>
				<h4 class="h4 font-bold">
					<i class="fa-solid fa-file-excel mr-2"></i>{m.dataWizardLoadExcelData()}
				</h4>
				<a
					class="text-indigo-600 hover:text-indigo-400"
					href="https://intuitem.gitbook.io/ciso-assistant/guide/data-import-wizard"
					>{m.dataWizardTemplatesAndGuidelines()}</a
				>
			</div>
			<div class=" py-4">
				<ol class="list-decimal list-inside">
					<li>{m.dataWizardSelectFile()}</li>
					<li>{m.dataWizardChooseModel()}</li>
					<li>{m.dataWizardSelectScope()}</li>
					<li>{m.dataWizardClickUpload()}</li>
				</ol>
			</div>
			<!-- Custom styled file input -->
			<div class="relative">
				<input
					id="file"
					type="file"
					name="file"
					accept={authorizedExtensions.join(',')}
					required
					bind:files
					class="sr-only"
				/>
				<label
					for="file"
					class="flex cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-6 text-center hover:border-gray-400 hover:bg-gray-100 transition-colors"
					class:border-blue-500={files && files.length > 0}
					class:bg-blue-50={files && files.length > 0}
				>
					<div class="space-y-2">
						<div
							class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gray-100"
						>
							<i class="fas fa-file-excel text-green-600 text-xl"></i>
						</div>
						<div class="text-sm">
							{#if files && files.length > 0}
								<p class="font-medium text-blue-600">
									<i class="fas fa-check-circle mr-1"></i>
									{files[0].name}
								</p>
								<p class="text-gray-500">
									{(files[0].size / 1024 / 1024).toFixed(2)} MB
								</p>
							{:else}
								<p class="font-medium text-gray-900">
									<span class="text-blue-600">{m.clickToUpload()}</span>
									{m.orDragAndDrop()}
								</p>
								<p class="text-gray-500">{m.fileAcceptExcelOnly()}</p>
							{/if}
						</div>
					</div>
				</label>
			</div>

			<div class="rounded-lg p-4 mt-4 border-green-500 border-2">
				<!--Model radio-->
				<fieldset class="space-y-4">
					<legend class="sr-only">{m.object()}</legend>

					<div>
						<label
							for="Asset"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
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
							for="User"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.users()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="User"
								id="User"
								class="size-5 border-gray-300 text-blue-500"
								bind:group={selectedModel}
							/>
						</label>
					</div>
					<div>
						<label
							for="AppliedControl"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
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
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
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
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
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
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.findingsAssessment()}</p>
								<p class="text-gray-500 text-xs">{m.dataWizardFindingsAssessmentDescription()}</p>
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

					<div>
						<label
							for="RiskAssessment"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.riskAssessment()}</p>
								<p class="text-gray-500 text-xs">{m.dataWizardRiskAssessmentDescription()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="RiskAssessment"
								id="RiskAssessment"
								class="size-5 border-gray-300 text-blue-500"
								bind:group={selectedModel}
							/>
						</label>
					</div>

					<div>
						<label
							for="ElementaryAction"
							class="flex cursor-pointer justify-between gap-4 rounded-lg border border-gray-100 bg-white p-4 text-sm font-medium shadow-2xs hover:border-gray-200 has-checked:border-blue-500 has-checked:ring-1 has-checked:ring-blue-500"
						>
							<div>
								<p class="text-gray-700">{m.elementaryActions()}</p>
								<p class="text-gray-500 text-xs">{m.dataWizardElementaryActionDescription()}</p>
							</div>

							<input
								type="radio"
								name="model"
								value="ElementaryAction"
								id="ElementaryAction"
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
					>{m.dataWizardSelectFallbackDomain()}</label
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
					>{m.dataWizardSelectPerimeter()}</label
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
					>{m.dataWizardSelectFramework()}</label
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

				<label for="matrix" class="block text-sm font-medium text-gray-900"
					>{m.dataWizardSelectRiskMatrix()}</label
				>
				<select
					id="matrix"
					name="matrix"
					disabled={isMatrixDisabled}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
				>
					{#each data.data.risk_matrices || [] as matrix}
						<option value={matrix.id}>{matrix.name}</option>
					{/each}
				</select>
			</div>
			<div class="flex py-4">
				<button
					class="btn preset-filled mt-2 lg:mt-0 {uploadButtonStyles}"
					type="button"
					onclick={modalConfirm}><i class="fa-solid fa-file-arrow-up mr-2"></i>{m.upload()}</button
				>
			</div>
		</form>
	</div>
	<div class="col-span-2 p-4">
		{m.dataWizardParsingResults()}
		{#if formSubmitted}
			<div class="col-span-full mb-4">
				{#if form?.success}
					<div class="alert alert-success preset-filled-success-500">
						<div>{form.message || 'File uploaded successfully'}</div>
					</div>
					<div class="text-xs font-mono p-2">{JSON.stringify(form?.results, null, 2)}</div>
				{:else}
					<div class="alert alert-error preset-filled-error-500">
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
