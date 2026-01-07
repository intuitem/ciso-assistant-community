<script lang="ts">
	import { LibraryUploadSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	import { page } from '$app/state';
	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { superValidate } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { tableHandlers } from '$lib/utils/stores';
	import UploadLibraryModal from '$lib/components/Modals/UploadLibraryModal.svelte';
	import {
		getModalStore,
		type ModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import { getModelInfo } from '$lib/utils/crud';

	import { safeTranslate } from '$lib/utils/i18n';

	let { data } = $props();

	// let fileResetSignal = $state(false);

	const modalStore: ModalStore = getModalStore();

	function modalCreateForm(): void {
		let modalComponent: ModalComponent = {
			ref: UploadLibraryModal
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('addYourLibrary')
		};
		modalStore.trigger(modal);
	}

	interface QuickFilters {
		object_type: Set<string>;
	}
	let quickFilterValues: QuickFilters = {
		object_type: new Set()
	};

	let quickFilterSelected: Record<string, boolean> = $state({});
</script>

<div class="card bg-white py-2 shadow-sm">
	<ModelTable
		source={data.storedLibrariesTable}
		URLModel="stored-libraries"
		deleteForm={data.deleteForm}
		onFilterChange={(filters) => {
			const objectTypeValues = filters['object_type'] ?? [];
			const filteredObjectTypes = objectTypeValues.map((filter) => filter.value);
			const filterKeys = Object.keys(quickFilterSelected);

			filterKeys.forEach((filterKey) => {
				quickFilterSelected[filterKey] = filteredObjectTypes.includes(filterKey);
			});
			filteredObjectTypes.forEach((filterKey) => {
				quickFilterSelected[filterKey] = true;
			});
		}}
	>
		{#snippet quickFilters(filterValues, form, invalidateTable)}
			<div
				class="flex flex-wrap gap-2 p-3 bg-gradient-to-r from-gray-50 to-white rounded-lg border border-gray-200"
			>
				{#each [{ key: 'frameworks', icon: 'fa-book-open', label: safeTranslate('frameworks'), selectedClass: 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-blue-200', hoverClass: 'hover:border-blue-400 hover:bg-blue-50' }, { key: 'reference_controls', icon: 'fa-shield-halved', label: safeTranslate('reference_controls'), selectedClass: 'bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-emerald-200', hoverClass: 'hover:border-emerald-400 hover:bg-emerald-50' }, { key: 'risk_matrices', icon: 'fa-table-cells', label: safeTranslate('risk_matrices'), selectedClass: 'bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-amber-200', hoverClass: 'hover:border-amber-400 hover:bg-amber-50' }, { key: 'threats', icon: 'fa-triangle-exclamation', label: safeTranslate('threats'), selectedClass: 'bg-gradient-to-r from-red-400 to-red-500 text-white shadow-red-200', hoverClass: 'hover:border-red-400 hover:bg-red-50' }, { key: 'metric_definitions', icon: 'fa-chart-line', label: safeTranslate('metric_definitions'), selectedClass: 'bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-purple-200', hoverClass: 'hover:border-purple-400 hover:bg-purple-50' }] as { key: objectType, icon, label, selectedClass, hoverClass }}
					<button
						class="group relative px-4 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 ease-out transform hover:scale-105 active:scale-95 shadow-sm hover:shadow-md {quickFilterSelected[
							objectType
						]
							? selectedClass
							: `bg-white text-gray-700 border-2 border-gray-300 ${hoverClass}`}"
						onclick={() => {
							const filterValue = filterValues['object_type'];
							const filteredTypes = filterValue.map((obj) => obj.value);

							const removeFilter = quickFilterValues.object_type.has(objectType);
							if (removeFilter) {
								quickFilterValues.object_type.delete(objectType);
								filterValues['object_type'] = filterValue.filter((obj) => obj.value !== objectType);
							} else {
								quickFilterValues.object_type.add(objectType);
								const isSelected = filteredTypes.includes(objectType);
								if (!isSelected) {
									filterValues['object_type'] = [...filterValue, { value: objectType }];
								}
							}

							const newFilteredTypes = filterValues['object_type'].map((obj) => obj.value);
							form.form.update((currentData) => {
								currentData['object_type'] = newFilteredTypes.length > 0 ? newFilteredTypes : null;
								return currentData;
							});

							invalidateTable();
						}}
					>
						<span class="flex items-center gap-2">
							<i
								class="fa-solid {icon} transition-transform duration-200 {quickFilterSelected[
									objectType
								]
									? 'scale-110'
									: 'group-hover:scale-110'}"
							></i>
							<span class="font-semibold">{label}</span>
							{#if quickFilterSelected[objectType]}
								<svg class="h-4 w-4 ml-1" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</span>
					</button>
				{/each}
			</div>
		{/snippet}
		{#snippet addButton()}
			<div>
				<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
					<button
						class="inline-block p-3 btn-mini-primary w-12 focus:relative"
						data-testid="add-button"
						title={m.addYourLibrary()}
						onclick={modalCreateForm}
						><i class="fa-solid fa-file-circle-plus"></i>
					</button>
				</span>
			</div>
		{/snippet}
	</ModelTable>
</div>
<!-- {#if page.data.user.is_admin}
	<div class="card bg-white p-4 mt-4 shadow-sm">
		{#await superValidate(zod(LibraryUploadSchema))}
			<h1>{m.loadingLibraryUploadButton()}...</h1>
		{:then form}
			<SuperForm
				class="flex flex-col space-y-3"
				dataType="form"
				enctype="multipart/form-data"
				data={form}
				validators={zod(LibraryUploadSchema)}
				action="?/upload"
				useFocusTrap={false}
				onSubmit={() => {
					const fileInput = document.querySelector(`input[type="file"]`);
					fileInput.value = '';
					fileResetSignal = true;
					setTimeout(() => {
						fileResetSignal = false;
					}, 10);
					// invalidate to show arrow update button
					Object.values($tableHandlers).forEach((handler) => {
						handler.invalidate();
					});
				}}
				{...rest}
			>
				{#snippet children({ form })}
					<FileInput
						{form}
						helpText={m.libraryFileInYaml()}
						field="file"
						label={m.addYourLibrary()}
						resetSignal={fileResetSignal}
						allowedExtensions={['yaml', 'yml']}
					/>
					<button
						class="btn preset-filled-primary-500 font-semibold w-full"
						data-testid="save-button"
						type="submit">{m.add()}</button
					>
				{/snippet}
			</SuperForm>
		{:catch err}
			<h1>{m.errorOccurredWhileLoadingLibrary()}: {err}</h1>
		{/await}
	</div>
{/if} -->
