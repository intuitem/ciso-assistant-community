<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages';

	const authorizedExtensions = ['.json'];
	import { getModalStore, type ModalSettings } from '@skeletonlabs/skeleton';

	const modalStore = getModalStore();

	let form: HTMLFormElement;
	let file: HTMLInputElement;

	function modalConfirmUpload(): void {
		const modal: ModalSettings = {
			type: 'confirm',
			title: m.importBackup(),
			body: m.confirmImportBackup(),
			response: (r: boolean) => form.requestSubmit()
		};
		if (file) modalStore.trigger(modal);
	}

	$: uploadButtonStyles = file ? '' : 'chip-disabled';

	const user = $page.data.user;
	const canBackup: boolean = Object.hasOwn(user.permissions, 'backup');
</script>

{#if canBackup}
	<div class=" flex grid grid-cols-2 space-x-4">
		<div class="card bg-white shadow py-4 px-6 space-y-2">
			<h4 class="h4 font-semibold">{m.exportBackup()} <i class="fa-solid fa-download" /></h4>
			<div class=" py-4">
				{m.exportBackupDescription()}
			</div>
			<form action="/backup-restore/dump-db/">
				<button type="submit" class="btn variant-filled-primary">{m.exportDatabase()}</button>
			</form>
		</div>

		<div class="card bg-white shadow py-4 px-6 space-y-2">
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
					class="btn variant-filled {uploadButtonStyles}"
					type="button"
					on:click={modalConfirmUpload}>{m.upload()}</button
				>
			</form>
		</div>
	</div>
{/if}
