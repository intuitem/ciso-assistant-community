<script lang="ts">
	import { LibraryUploadSchema } from '$lib/utils/schemas';

	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { superValidate } from 'sveltekit-superforms/server';

	export let data;

	import { TabGroup, Tab } from '@skeletonlabs/skeleton';
	let tabSet: number = data.importedLibrariesTable.body.length > 0 ? 0 : 1;
	$: if (data.importedLibrariesTable.body.length === 0) tabSet = 1;
</script>

<div class="card bg-white shadow">
	<TabGroup>
		{#if data.importedLibrariesTable.body.length > 0}
			<Tab bind:group={tabSet} value={0}>Imported libraries</Tab>
			<Tab bind:group={tabSet} value={1}>Libraries store</Tab>
		{:else}
			<div class="card p-4 variant-soft-secondary w-full m-4">
				<i class="fa-solid fa-info-circle mr-2" />
				You currently have no imported libraries.
			</div>
		{/if}
		<svelte:fragment slot="panel">
			{#if tabSet === 0}
				<ModelTable
					source={data.importedLibrariesTable}
					URLModel="libraries"
					identifierField="urn"
					deleteForm={data.deleteForm}
					pagination={false}
				/>
			{/if}
			{#if tabSet === 1}
				<ModelTable
					source={data.defaultLibrariesTable}
					URLModel="libraries"
					identifierField="urn"
					pagination={false}
				/>
			{/if}
		</svelte:fragment>
	</TabGroup>
</div>
{#if tabSet === 1}
	<div class="card bg-white p-4 mt-4 shadow">
		{#await superValidate(LibraryUploadSchema)}
			<h1>Loading the library upload button...</h1>
		{:then form}
			<SuperForm
				class="flex flex-col space-y-3"
				dataType="form"
				enctype="multipart/form-data"
				data={form}
				let:form
				validators={LibraryUploadSchema}
				action="?/upload"
				{...$$restProps}
			>
				<FileInput
					{form}
					helpText="Library file in YAML format"
					mandatory={true}
					field="file"
					label="Upload your own library :"
				/>

				<button
					class="btn variant-filled-primary font-semibold w-full"
					data-testid="save-button"
					type="submit">Save</button
				>
			</SuperForm>
		{:catch err}
			<h1>The following error occured while loading the library form : {err}</h1>
		{/await}
	</div>
{/if}
