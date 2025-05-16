<script lang="ts">
	import { run } from 'svelte/legacy';

	import { LibraryUploadSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	import { page } from '$app/state';
	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import { superValidate } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';

	let { data, ...rest } = $props();

	let group: 'stored' | 'loaded' = $state(
		data.loadedLibrariesTable.meta.count > 0 ? 'stored' : 'loaded'
	);

	let fileResetSignal = $state(false);

	let availableUpdatesCount = $derived(data?.updatableLibraries?.length);

	run(() => {
		if (data.loadedLibrariesTable.meta.count === 0) group = 'stored';
	});
</script>

<div class="card bg-white shadow-sm">
	<Tabs value={group} onValueChange={(e) => (group = e.value)} listJustify="justify-center">
		{#snippet list()}
			<Tabs.Control value="stored"
				>{m.librariesStore()}
				<span class="badge preset-tonal-primary">{data.storedLibrariesTable.meta.count}</span
				></Tabs.Control
			>
			<Tabs.Control value="loaded"
				>{m.loadedLibraries()}
				<span class="badge preset-tonal-primary">{data.loadedLibrariesTable.meta.count}</span>
				{#if availableUpdatesCount > 0}
					<span class="badge preset-tonal-success"
						>{availableUpdatesCount} <i class="fa-solid fa-circle-up ml-1"></i></span
					>
				{/if}
			</Tabs.Control>
		{/snippet}
		{#if data.loadedLibrariesTable.meta.count < 0}
			<div class="card p-4 preset-tonal-secondary w-full m-4">
				<i class="fa-solid fa-info-circle mr-2"></i>
				{m.currentlyNoLoadedLibraries()}.
			</div>
		{/if}

		{#snippet content()}
			<Tabs.Panel value="stored">
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
			</Tabs.Panel>
			<Tabs.Panel value="loaded">
				<ModelTable
					source={data.loadedLibrariesTable}
					URLModel="loaded-libraries"
					deleteForm={data.deleteForm}
					detailQueryParameter="loaded"
					server={false}
				/>
			</Tabs.Panel>
		{/snippet}
	</Tabs>
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
