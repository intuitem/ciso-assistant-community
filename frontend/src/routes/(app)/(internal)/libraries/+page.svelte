<script lang="ts">
	import { LibraryUploadSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages';

	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { superValidate } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';

	export let data;

	import { TabGroup, Tab } from '@skeletonlabs/skeleton';
	let tabSet: number = data.loadedLibrariesTable.body.length > 0 ? 0 : 1;
	$: if (data.loadedLibrariesTable.body.length === 0) tabSet = 0;

	let fileResetSignal = false;
</script>

<div class="card bg-white shadow">
	<TabGroup>
		<!-- data.loadedLibrariesTable.body.length > 0 -->
		{#if data.loadedLibrariesTable.body.length > 0}
			<Tab bind:group={tabSet} value={0}>{m.librariesStore()}</Tab>
			<Tab bind:group={tabSet} value={1}>{m.loadedLibraries()}</Tab>
		{:else}
			<div class="card p-4 variant-soft-secondary w-full m-4">
				<i class="fa-solid fa-info-circle mr-2" />
				{m.currentlyNoLoadedLibraries()}.
			</div>
		{/if}
		<svelte:fragment slot="panel">
			<!-- storedlibraries -->
			{#if tabSet === 0}
				<ModelTable
					source={data.storedLibrariesTable}
					URLModel="libraries"
					identifierField="id"
					pagination={false}
					deleteForm={data.deleteForm}
				/>
			{/if}
			{#if tabSet === 1}
				<!-- loadedlibraries -->
				<ModelTable
					source={data.loadedLibrariesTable}
					URLModel="libraries"
					identifierField="id"
					pagination={false}
					deleteForm={data.deleteForm}
					detailQueryParameter="loaded"
				/>
			{/if}
		</svelte:fragment>
	</TabGroup>
</div>
{#if tabSet === 0}
	<div class="card bg-white p-4 mt-4 shadow">
		{#await superValidate(zod(LibraryUploadSchema))}
			<h1>{m.loadingLibraryUploadButton()}...</h1>
		{:then form}
			<SuperForm
				class="flex flex-col space-y-3"
				dataType="form"
				enctype="multipart/form-data"
				data={form}
				let:form
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
				{...$$restProps}
			>
				<FileInput
					{form}
					helpText={m.libraryFileInYaml()}
					field="file"
					label={m.addYourLibrary()}
					resetSignal={fileResetSignal}
				/>

				<button
					class="btn variant-filled-primary font-semibold w-full"
					data-testid="save-button"
					type="submit">{m.add()}</button
				>
			</SuperForm>
		{:catch err}
			<h1>{m.errorOccuredWhileLoadingLibrary()}: {err}</h1>
		{/await}
	</div>
{/if}
