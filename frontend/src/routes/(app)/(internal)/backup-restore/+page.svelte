<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	export let data: PageData;

	import type { ModalSettings, ModalComponent, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';

	const modalStore: ModalStore = getModalStore();

	let form: HTMLFormElement;
	let file: HTMLInputElement;

	// Function to handle modal confirmation for any action
	function modalConfirm(): void {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal
		};

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.importBackup(),
			body: m.confirmImportBackup(),
			response: (r: boolean) => {
				if (r) form.requestSubmit();
			}
		};

		if (file) modalStore.trigger(modal);
	}

	$: uploadButtonStyles = file ? '' : 'chip-disabled';

	const authorizedExtensions = ['.bak'];
	const user = $page.data.user;
	const canBackup: boolean = Object.hasOwn(user.permissions, 'backup');
</script>

{#if canBackup}
	<div class="grid grid-cols-2 space-y-2 lg:space-y-0 lg:space-x-4">
		<div class="card col-span-full lg:col-span-1 bg-white shadow py-4 px-6 space-y-2">
			<h4 class="h4 font-semibold">{m.exportBackup()} <i class="fa-solid fa-download" /></h4>
			<div class=" py-4">
				{m.exportBackupDescription()}
			</div>
			<form action="/backup-restore/dump-db/">
				<button type="submit" class="btn variant-filled-primary">{m.exportDatabase()}</button>
			</form>
		</div>

		<div class="card col-span-full lg:col-span-1 bg-white shadow py-4 px-6 space-y-2">
			<h4 class="h4 font-semibold">{m.importBackup()} <i class="fa-solid fa-upload" /></h4>
			<div class=" py-4">
				{m.importBackupDescription()}
			</div>
			<form enctype="multipart/form-data" method="post" use:enhance bind:this={form}>
				<input
					id="file"
					type="file"
					name="file"
					accept={authorizedExtensions.join(',')}
					required
					bind:value={file}
				/>
				<button
					class="btn variant-filled mt-2 lg:mt-0 {uploadButtonStyles}"
					type="button"
					on:click={modalConfirm}>{m.upload()}</button
				>
			</form>
		</div>
	</div>
{/if}
