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

	import { safeTranslate } from '$lib/utils/i18n';

	let { data, ...rest } = $props();

	let group: 'stored' | 'loaded' = $state(
		data.loadedLibrariesTable.meta.count > 0 ? 'stored' : 'loaded'
	);

	let fileResetSignal = $state(false);

	let availableUpdatesCount = $derived(data?.updatableLibraries?.length);

	$effect(() => {
		if (data.loadedLibrariesTable.meta.count === 0) group = 'stored';
	});
	let mappingSuggestedCount = $derived(data?.mappingSuggested?.length);

	interface QuickFilters {
		object_type: Set<string>;
	}
	let quickFilterValues: QuickFilters = $state({
		object_type: new Set()
	});
</script>

<div class="card bg-white py-2 shadow-sm">
	<ModelTable
		source={data.storedLibrariesTable}
		URLModel="stored-libraries"
		deleteForm={data.deleteForm}
	>
		{#snippet quickFilters(filterValues, form, invalidateTable)}
			{#each ['frameworks', 'reference_controls', 'risk_matrices', 'threats'] as objectType}
				<button
					class="p-4 border-2 border-black"
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
		{/snippet}
	</ModelTable>
</div>
{#if group === 'stored' && page.data.user.is_admin}
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
{/if}
