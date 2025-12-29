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
			<div class="flex gap-1">
				{#each ['frameworks', 'reference_controls', 'risk_matrices', 'threats', 'metric_definitions'] as objectType}
					<button
						class="ml-2 p-2 border-2 rounded-lg {quickFilterSelected[objectType]
							? 'border-primary-800'
							: 'border-primary-100 hover:border-primary-500'}"
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
						}}>{safeTranslate(objectType)}</button
					>
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
