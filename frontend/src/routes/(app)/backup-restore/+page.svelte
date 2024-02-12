<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';

	const authorizedExtensions = ['.json'];
	import { getModalStore, type ModalSettings } from '@skeletonlabs/skeleton';

	const modalStore = getModalStore();

	let form: HTMLFormElement;
	let file: HTMLInputElement;

	function modalConfirmUpload(): void {
		const modal: ModalSettings = {
			type: 'confirm',
			title: 'Import backup?',
			body: 'Are you sure you want to import this backup? This will overwrite all existing data.',
			response: (r: boolean) => form.requestSubmit()
		};
		if (file) modalStore.trigger(modal);
	}

	$: uploadButtonStyles = file ? '' : 'chip-disabled';

	const user = $page.data.user;
	const canBackup: boolean = Object.hasOwn(user.permissions, 'backup');
</script>

{#if canBackup}
	<div class="card bg-white shadow py-4 px-6 space-y-2">
		<h4 class="h4 font-semibold">Export backup</h4>
		<form action="/backup-restore/dump-db/">
			<button type="submit" class="btn variant-filled-primary">Dump database</button>
		</form>
	</div>

	<div class="card bg-white shadow py-4 px-6 space-y-2">
		<h4 class="h4 font-semibold">Import backup</h4>
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
				on:click={modalConfirmUpload}>Upload</button
			>
		</form>
	</div>
{/if}
