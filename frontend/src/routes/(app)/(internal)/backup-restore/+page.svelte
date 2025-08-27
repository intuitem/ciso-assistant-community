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
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	let form: HTMLFormElement = $state();
	let file: HTMLInputElement = $state();
	let isExporting = $state(false);
	let isUploading = $state(false);

	// Function to handle modal confirmation for any action
	function modalConfirm(): void {
		if (isUploading) return; // Prevent multiple clicks

		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal
		};

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.importBackup(),
			body: m.confirmImportBackup(),
			response: (r: boolean) => {
				if (r) {
					isUploading = true;
					form.requestSubmit();
				}
			}
		};

		if (file) modalStore.trigger(modal);
	}

	let uploadButtonStyles = $derived(file && !isUploading ? '' : 'chip-disabled');
	let exportButtonStyles = $derived(isExporting ? 'chip-disabled' : '');

	const authorizedExtensions = ['.bak'];
	const user = page.data.user;
	const canBackup: boolean = Object.hasOwn(user.permissions, 'backup');
</script>

{#if canBackup}
	<div class="grid grid-cols-2 space-y-2 lg:space-y-0 lg:space-x-4">
		<div class="card col-span-full lg:col-span-1 bg-white shadow-sm py-4 px-6 space-y-2">
			<h4 class="h4 font-semibold">{m.exportBackup()} <i class="fa-solid fa-download"></i></h4>
			<div class=" py-4">
				{m.exportBackupDescription()}
			</div>
			<form
				action="/backup-restore/dump-db/"
				onsubmit={() => {
					if (!isExporting) {
						isExporting = true;
						setTimeout(() => {
							isExporting = false;
						}, 3000);
					}
				}}
			>
				<button
					type="submit"
					class="btn preset-filled-primary-500 {exportButtonStyles}"
					disabled={isExporting}
				>
					{#if isExporting}
						<i class="fa-solid fa-spinner fa-spin"></i>
						{m.exporting ? m.exporting() : 'Exporting...'}
					{:else}
						{m.exportDatabase()}
					{/if}
				</button>
			</form>
		</div>

		<div class="card col-span-full lg:col-span-1 bg-white shadow-sm py-4 px-6 space-y-2">
			<h4 class="h4 font-semibold">{m.importBackup()} <i class="fa-solid fa-upload"></i></h4>
			<div class=" py-4">
				{m.importBackupDescription()}
			</div>
			<form
				enctype="multipart/form-data"
				method="post"
				use:enhance={() => {
					return async ({ update }) => {
						await update();
						isUploading = false;
					};
				}}
				bind:this={form}
			>
				<div class="flex flex-col sm:flex-row sm:items-end gap-3">
					<div class="flex-1">
						<input
							id="file"
							type="file"
							name="file"
							class="input"
							accept={authorizedExtensions.join(',')}
							required
							bind:value={file}
						/>
					</div>
					<button
						class="btn preset-filled-secondary-500 {uploadButtonStyles}"
						type="button"
						disabled={isUploading}
						onclick={modalConfirm}
					>
						{#if isUploading}
							<i class="fa-solid fa-spinner fa-spin"></i>
							{m.uploading ? m.uploading() : 'Uploading...'}
						{:else}
							{m.upload()}
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}
