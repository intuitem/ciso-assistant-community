<script lang="ts">
	import { run } from 'svelte/legacy';

	import { LibraryUploadSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	import { page } from '$app/stores';
	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { Tab, TabGroup } from '@skeletonlabs/skeleton';
	import { superValidate } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';

	let { data, ...rest } = $props();

	let tabSet: number = $state(data.loadedLibrariesTable.meta.count > 0 ? 0 : 1);

	let fileResetSignal = $state(false);

	let availableUpdatesCount = $derived(data?.updatableLibraries?.length);

	run(() => {
		if (data.loadedLibrariesTable.meta.count === 0) tabSet = 0;
	});
</script>

<div class="card bg-white shadow">
	<TabGroup>
		{#if data.loadedLibrariesTable.meta.count > 0}
			<Tab bind:group={tabSet} value={0}
				>{m.librariesStore()}
				<span class="badge variant-soft-primary">{data.storedLibrariesTable.meta.count}</span></Tab
			>
			<Tab bind:group={tabSet} value={1}
				>{m.loadedLibraries()}
				<span class="badge variant-soft-primary">{data.loadedLibrariesTable.meta.count}</span>
				{#if availableUpdatesCount > 0}
					<span class="badge variant-soft-success"
						>{availableUpdatesCount} <i class="fa-solid fa-circle-up ml-1"></i></span
					>
				{/if}
			</Tab>
		{:else}
			<div class="card p-4 variant-soft-secondary w-full m-4">
				<i class="fa-solid fa-info-circle mr-2"></i>
				{m.currentlyNoLoadedLibraries()}.
			</div>
		{/if}
		{#snippet panel()}
			
				<!-- storedlibraries -->
				{#if tabSet === 0}
					<div class="flex items-center mb-2 px-2 text-xs space-x-2">
						<i class="fa-solid fa-info-circle"></i>
						<p>{m.librariesCanOnlyBeLoadedByAdmin()}</p>
					</div>
					<ModelTable
						source={data.storedLibrariesTable}
						URLModel="stored-libraries"
						deleteForm={data.deleteForm}
						server={false}
					/>
				{/if}
				{#if tabSet === 1}
					<!-- loadedlibraries -->
					<ModelTable
						source={data.loadedLibrariesTable}
						URLModel="loaded-libraries"
						deleteForm={data.deleteForm}
						detailQueryParameter="loaded"
						server={false}
					/>
				{/if}
			
			{/snippet}
	</TabGroup>
</div>
{#if tabSet === 0 && $page.data.user.is_admin}
	<div class="card bg-white p-4 mt-4 shadow">
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
						class="btn variant-filled-primary font-semibold w-full"
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
