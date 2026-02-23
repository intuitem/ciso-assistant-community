<script lang="ts">
	import { LibraryUploadSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';

	import { page } from '$app/state';
	import FileInput from '$lib/components/Forms/FileInput.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { superValidate } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { tableHandlers } from '$lib/utils/stores';
	import { getModalStore } from './stores';

	const modalStore = getModalStore();

	let fileResetSignal = $state(false);

	let { parent } = $props();
</script>

{#if page.data.user.is_admin}
	<div class="card bg-white p-6 w-full max-w-lg shadow-xl space-y-4 rounded-xl">
		<div class="flex items-center justify-between">
			<header class="flex items-center gap-3">
				<div
					class="flex items-center justify-center w-10 h-10 rounded-lg bg-primary-100 text-primary-600"
				>
					<i class="fa-solid fa-file-circle-plus text-lg"></i>
				</div>
				<h3 class="text-xl font-bold text-gray-800">
					{m.customExternalLibrary()}
				</h3>
			</header>
			<button
				type="button"
				class="flex items-center justify-center w-8 h-8 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
				onclick={parent.onClose}
				aria-label="Close"
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</div>
		<p class="text-sm text-gray-500">{m.libraryAddHelpText()}</p>
		<hr class="border-gray-200" />
		{#await superValidate(zod(LibraryUploadSchema))}
			<p class="text-gray-500">{m.loadingLibraryUploadButton()}...</p>
		{:then form}
			<SuperForm
				class="flex flex-col space-y-4"
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
					parent.onClose();
				}}
			>
				{#snippet children({ form })}
					<FileInput
						{form}
						helpText={m.libraryFileInYamlOrXlsx()}
						field="file"
						label={m.addYourLibrary()}
						resetSignal={fileResetSignal}
						allowedExtensions={['yaml', 'yml', 'xlsx']}
					/>
					<button
						class="btn preset-filled-primary-500 font-semibold w-full rounded-lg py-2.5"
						data-testid="save-button"
						type="submit"
					>
						<i class="fa-solid fa-upload mr-2"></i>
						{m.add()}
					</button>
				{/snippet}
			</SuperForm>
		{:catch err}
			<p class="text-red-600">{m.errorOccurredWhileLoadingLibrary()}: {err}</p>
		{/await}
	</div>
{/if}
