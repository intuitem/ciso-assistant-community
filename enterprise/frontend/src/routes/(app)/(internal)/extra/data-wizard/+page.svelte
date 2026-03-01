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

	let formElement: HTMLFormElement | null = $state(null);
	let files: FileList | null = $state(null); // Fixed: Changed from HTMLInputElement to FileList
	let selectedModel = $state('Asset'); // Default selection
	let searchQuery = $state('');
	let showModelDropdown = $state(false);
	let searchInputRef: HTMLInputElement | null = $state(null);
	let onConflict = $state('stop');

	// Model configuration
	const modelOptions = [
		{ id: 'Asset', label: m.assets(), description: '' },
		{ id: 'User', label: m.users(), description: '' },
		{ id: 'AppliedControl', label: m.appliedControls(), description: '' },
		{ id: 'Policy', label: m.policies(), description: '' },
		{ id: 'Folder', label: m.domains(), description: '' },
		{ id: 'Perimeter', label: m.perimeters(), description: '' },
		{ id: 'ComplianceAssessment', label: m.complianceAssessment(), description: '' },
		{
			id: 'FindingsAssessment',
			label: m.findingsAssessment(),
			description: m.dataWizardFindingsAssessmentDescription()
		},
		{
			id: 'RiskAssessment',
			label: m.riskAssessment(),
			description: m.dataWizardRiskAssessmentDescription()
		},
		{
			id: 'ElementaryAction',
			label: m.elementaryActions(),
			description: m.dataWizardElementaryActionDescription()
		},
		{ id: 'Vulnerability', label: m.vulnerabilities(), description: '' },
		{ id: 'ReferenceControl', label: m.referenceControls(), description: '' },
		{ id: 'Threat', label: m.threats(), description: '' },
		{ id: 'Processing', label: m.processings(), description: '' },
		{ id: 'SecurityException', label: m.securityExceptions(), description: '' },
		{ id: 'Incident', label: m.incidents(), description: '' },
		{
			id: 'TPRM',
			label: m.thirdPartyCategory(),
			description: m.thirdPartiesImportHelpText()
		},
		{
			id: 'EbiosRMStudyARM',
			label: m.ebiosRMStudyARM(),
			description: m.ebiosRMStudyARMDescription()
		},
		{
			id: 'EbiosRMStudyExcel',
			label: m.ebiosRMStudyExcel(),
			description: m.ebiosRMStudyExcelDescription()
		}
	];

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
				if (r) formElement?.requestSubmit();
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
			selectedModel === 'RiskAssessment' ||
			selectedModel === 'User' ||
			selectedModel === 'Folder'
	);

	let isFrameworkDisabled = $derived(selectedModel !== 'ComplianceAssessment');

	let isMatrixDisabled = $derived(
		selectedModel !== 'RiskAssessment' &&
			selectedModel !== 'EbiosRMStudyARM' &&
			selectedModel !== 'EbiosRMStudyExcel'
	);

	// Models that don't need perimeter selection
	const modelsWithoutPerimeter = [
		'Folder',
		'User',
		'Asset',
		'AppliedControl',
		'Policy',
		'Perimeter',
		'ElementaryAction',
		'ReferenceControl',
		'Threat',
		'Processing',
		'SecurityException',
		'Incident',
		'TPRM',
		'EbiosRMStudyARM',
		'EbiosRMStudyExcel',
		'Vulnerability'
	];

	// Determine if perimeter selection should be disabled
	let isPerimeterDisabled = $derived(modelsWithoutPerimeter.includes(selectedModel));

	// Fixed: Check files correctly
	let uploadButtonStyles = $derived(files && files.length > 0 ? '' : 'chip-disabled');

	// Helper to check if the form has been processed (form action has run)
	let formSubmitted = $derived(form !== null && form !== undefined);

	const authorizedExtensions = ['.xls', '.xlsx'];

	// Filter models based on search query
	let filteredModels = $derived(
		searchQuery.length > 0
			? modelOptions.filter(
					(model) =>
						model.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
						model.description.toLowerCase().includes(searchQuery.toLowerCase())
				)
			: modelOptions
	);

	// Get currently selected model info
	let selectedModelInfo = $derived(modelOptions.find((m) => m.id === selectedModel));

	// Close dropdown when clicking outside
	function handleClickOutside(e: any) {
		if (!e.target.closest('[data-model-selector]')) {
			showModelDropdown = false;
		}
	}

	// Focus search input when dropdown opens
	$effect(() => {
		if (showModelDropdown && searchInputRef) {
			searchInputRef.focus();
		}
	});
</script>

<div class="grid grid-cols-4 gap-4" onclick={handleClickOutside}>
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
								</p>
								<p class="text-gray-500">{m.fileAcceptExcelOnly()}</p>
							{/if}
						</div>
					</div>
				</label>
			</div>

			<div
				class="rounded-lg p-6 mt-6 border-2 border-indigo-200 bg-gradient-to-br from-indigo-50 to-white"
			>
				<!-- Model Selection Header -->
				<div class="mb-4">
					<label class="block text-sm font-semibold text-gray-900 mb-2">{m.object()}</label>
					<p class="text-xs text-gray-600 mb-3">{m.dataWizardChooseModel()}</p>
				</div>

				<!-- Searchable Model Selector -->
				<div class="relative" data-model-selector="true">
					<!-- Selected Model Display -->
					<button
						type="button"
						onclick={() => (showModelDropdown = !showModelDropdown)}
						class="w-full px-4 py-3 text-left bg-white border-2 border-gray-300 rounded-lg hover:border-indigo-400 transition-colors focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-3 flex-1 min-w-0">
								{#if selectedModelInfo}
									<div class="flex-1 min-w-0">
										<p class="font-medium text-gray-900 truncate">{selectedModelInfo.label}</p>
										{#if selectedModelInfo.description}
											<p class="text-xs text-gray-500 truncate">{selectedModelInfo.description}</p>
										{/if}
									</div>
								{/if}
							</div>
							<svg
								class="h-5 w-5 text-gray-400 transition-transform {showModelDropdown
									? 'rotate-180'
									: ''}"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M19 14l-7 7m0 0l-7-7m7 7V3"
								></path>
							</svg>
						</div>
					</button>

					<!-- Dropdown Panel -->
					{#if showModelDropdown}
						<div
							class="absolute z-50 w-full mt-2 bg-white border-2 border-indigo-300 rounded-lg shadow-lg"
							onclick={(e) => e.stopPropagation()}
						>
							<!-- Search Input -->
							<div class="p-3 border-b border-gray-200 sticky top-0 bg-white rounded-t-lg">
								<input
									type="text"
									placeholder={m.searchPlaceholder()}
									bind:this={searchInputRef}
									bind:value={searchQuery}
									autofocus
									class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-200"
								/>
							</div>

							<!-- Model Options Grid -->
							<div class="max-h-96 overflow-y-auto">
								{#if filteredModels.length > 0}
									{#each filteredModels as model (model.id)}
										<button
											type="button"
											onclick={() => {
												selectedModel = model.id;
												showModelDropdown = false;
												searchQuery = '';
											}}
											class="w-full px-4 py-3 text-left hover:bg-indigo-50 border-b border-gray-100 last:border-b-0 transition-colors group"
											class:bg-indigo-100={model.id === selectedModel}
										>
											<div class="flex items-start gap-3">
												<div class="flex-1 min-w-0 pt-0.5">
													<p
														class="font-medium text-gray-900 group-hover:text-indigo-700 transition-colors"
														class:text-indigo-700={model.id === selectedModel}
													>
														{model.label}
													</p>
													{#if model.description}
														<p class="text-xs text-gray-500 mt-0.5">{model.description}</p>
													{/if}
												</div>
												{#if model.id === selectedModel}
													<div class="flex-shrink-0 mt-1">
														<svg
															class="h-5 w-5 text-indigo-600"
															fill="currentColor"
															viewBox="0 0 20 20"
														>
															<path
																fill-rule="evenodd"
																d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
																clip-rule="evenodd"
															></path>
														</svg>
													</div>
												{/if}
											</div>
										</button>
									{/each}
								{:else}
									<div class="px-4 py-8 text-center text-gray-500">
										<p class="text-sm">{m.noResultsFound?.() ?? 'No results found'}</p>
									</div>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Hidden select for form submission -->
					<select name="model" bind:value={selectedModel} class="sr-only">
						{#each modelOptions as model}
							<option value={model.id}>{model.label}</option>
						{/each}
					</select>
				</div>

				<!-- Selected Model Description -->
				{#if selectedModelInfo?.description}
					<div class="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
						<p class="text-xs text-blue-900">{selectedModelInfo.description}</p>
					</div>
				{/if}
			</div>

			<!-- On-Conflict Handling -->
			<div
				class="rounded-lg p-6 mt-6 border-2 border-amber-200 bg-gradient-to-br from-amber-50 to-white"
			>
				<label class="block text-sm font-semibold text-gray-900 mb-3"
					>{m.dataWizardOnConflict()}</label
				>
				<div class="flex gap-2">
					<label
						class="flex-1 cursor-pointer rounded-lg border-2 px-3 py-2 text-center text-sm transition-colors {onConflict ===
						'stop'
							? 'border-amber-500 bg-amber-100 font-semibold text-amber-800'
							: 'border-gray-200 bg-white text-gray-700 hover:border-amber-300'}"
					>
						<input
							type="radio"
							name="onConflictRadio"
							value="stop"
							bind:group={onConflict}
							class="sr-only"
						/>
						<div class="font-medium">{m.dataWizardOnConflictStop()}</div>
						<div class="text-xs text-gray-500 mt-0.5">
							{m.dataWizardOnConflictStopDescription()}
						</div>
					</label>
					<label
						class="flex-1 cursor-pointer rounded-lg border-2 px-3 py-2 text-center text-sm transition-colors {onConflict ===
						'skip'
							? 'border-amber-500 bg-amber-100 font-semibold text-amber-800'
							: 'border-gray-200 bg-white text-gray-700 hover:border-amber-300'}"
					>
						<input
							type="radio"
							name="onConflictRadio"
							value="skip"
							bind:group={onConflict}
							class="sr-only"
						/>
						<div class="font-medium">{m.dataWizardOnConflictSkip()}</div>
						<div class="text-xs text-gray-500 mt-0.5">
							{m.dataWizardOnConflictSkipDescription()}
						</div>
					</label>
					<label
						class="flex-1 cursor-pointer rounded-lg border-2 px-3 py-2 text-center text-sm transition-colors {onConflict ===
						'update'
							? 'border-amber-500 bg-amber-100 font-semibold text-amber-800'
							: 'border-gray-200 bg-white text-gray-700 hover:border-amber-300'}"
					>
						<input
							type="radio"
							name="onConflictRadio"
							value="update"
							bind:group={onConflict}
							class="sr-only"
						/>
						<div class="font-medium">{m.dataWizardOnConflictUpdate()}</div>
						<div class="text-xs text-gray-500 mt-0.5">
							{m.dataWizardOnConflictUpdateDescription()}
						</div>
					</label>
				</div>
				<input type="hidden" name="onConflict" value={onConflict} />
			</div>

			<div
				class="rounded-lg p-6 mt-6 border-2 border-rose-200 bg-gradient-to-br from-rose-50 to-white space-y-4"
			>
				<!-- Targets Section -->
				<div>
					<h3 class="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
						<i class="fa-regular fa-circle-dot mr-2"></i>
						{m.dataWizardSelectScope()}
					</h3>
				</div>

				<!-- Domain Selection -->
				<div>
					<label for="folder" class="block text-sm font-medium text-gray-900 mb-2"
						>{m.dataWizardSelectFallbackDomain()}</label
					>
					{#if !isDomainDisabled}
						<select
							id="folder"
							name="folder"
							class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg text-gray-900 text-sm hover:border-rose-400 focus:outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-200 transition-colors"
						>
							{#each data.data.folders as folder}
								<option value={folder.id}>{folder.name}</option>
							{/each}
						</select>
					{:else}
						<div
							class="px-4 py-2.5 bg-gray-100 border-2 border-gray-200 rounded-lg text-gray-500 text-sm"
						>
							{m.automatic?.() ?? 'Automatic'}
						</div>
					{/if}
				</div>

				<!-- Perimeter Selection -->
				<div>
					<label for="perimeter" class="block text-sm font-medium text-gray-900 mb-2"
						>{m.dataWizardSelectPerimeter()}</label
					>
					{#if !isPerimeterDisabled}
						<select
							id="perimeter"
							name="perimeter"
							class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg text-gray-900 text-sm hover:border-rose-400 focus:outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-200 transition-colors"
						>
							{#each data.data.perimeters as perimeter}
								<option value={perimeter.id}>{perimeter.name}</option>
							{/each}
						</select>
					{:else}
						<div
							class="px-4 py-2.5 bg-gray-100 border-2 border-gray-200 rounded-lg text-gray-500 text-sm"
						>
							{m.notRequired?.() ?? 'Not required'}
						</div>
					{/if}
				</div>

				<!-- Framework Selection -->
				<div>
					<label for="framework" class="block text-sm font-medium text-gray-900 mb-2"
						>{m.dataWizardSelectFramework()}</label
					>
					{#if !isFrameworkDisabled}
						<select
							id="framework"
							name="framework"
							class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg text-gray-900 text-sm hover:border-rose-400 focus:outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-200 transition-colors"
						>
							{#each data.data.frameworks as framework}
								<option value={framework.id}>{framework.name}</option>
							{/each}
						</select>
					{:else}
						<div
							class="px-4 py-2.5 bg-gray-100 border-2 border-gray-200 rounded-lg text-gray-500 text-sm"
						>
							{m.notRequired?.() ?? 'Not required'}
						</div>
					{/if}
				</div>

				<!-- Risk Matrix Selection -->
				<div>
					<label for="matrix" class="block text-sm font-medium text-gray-900 mb-2"
						>{m.dataWizardSelectRiskMatrix()}</label
					>
					{#if !isMatrixDisabled}
						<select
							id="matrix"
							name="matrix"
							class="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg text-gray-900 text-sm hover:border-rose-400 focus:outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-200 transition-colors"
						>
							{#each data.data.risk_matrices || [] as matrix}
								<option value={matrix.id}>{matrix.name}</option>
							{/each}
						</select>
					{:else}
						<div
							class="px-4 py-2.5 bg-gray-100 border-2 border-gray-200 rounded-lg text-gray-500 text-sm"
						>
							{m.notRequired?.() ?? 'Not required'}
						</div>
					{/if}
				</div>
			</div>

			<!-- Upload Button -->
			<div class="flex gap-3 py-6">
				<button
					class="flex-1 px-6 py-3 bg-gradient-to-r {uploadButtonStyles} from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white font-semibold rounded-lg transition-all duration-200 shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
					type="button"
					disabled={!files || files.length === 0}
					onclick={modalConfirm}
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3v-6"
						></path>
					</svg>
					{m.upload()}
				</button>
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
					<p class="wrap-break-word break-all whitespace-pre-wrap font-mono p-2">
						{JSON.stringify(form?.results, null, 2)}
					</p>
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
