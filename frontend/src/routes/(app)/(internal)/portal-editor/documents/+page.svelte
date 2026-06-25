<script lang="ts">
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();
	const toast = getToastStore();

	function humanSize(bytes: number) {
		if (!bytes) return '—';
		const units = ['B', 'KB', 'MB', 'GB'];
		let n = bytes;
		let i = 0;
		while (n >= 1024 && i < units.length - 1) {
			n /= 1024;
			i++;
		}
		return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
	}

	function confirmDelete(e: MouseEvent, name: string) {
		const form = (e.currentTarget as HTMLElement).closest('form') as HTMLFormElement;
		const modal: ModalSettings = {
			type: 'confirm',
			title: m.delete(),
			body: m.deleteModalMessage({ name }),
			buttonTextConfirm: m.delete(),
			response: (confirmed: boolean) => {
				if (confirmed) form.requestSubmit();
			}
		};
		modalStore.trigger(modal);
	}
</script>

<div class="space-y-6">
	<div class="flex items-center gap-3">
		<a href="/portal-editor" class="text-surface-500 hover:text-primary-500">
			<i class="fa-solid fa-arrow-left"></i>
		</a>
		<h1 class="text-lg font-bold">{m.publicDocuments()}</h1>
	</div>
	<p class="text-sm text-surface-500">{m.publicDocumentsHelp()}</p>

	<section class="card bg-surface-50-950 p-6">
		<form
			method="POST"
			action="?/upload"
			enctype="multipart/form-data"
			use:enhance={() =>
				async ({ result, update }) => {
					await update();
					if (result.type === 'success')
						toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });
				}}
			class="flex flex-wrap items-end gap-3"
		>
			<label class="text-xs text-surface-500">
				<span class="block">{m.name()}</span>
				<input name="name" required class="input rounded-md text-sm" />
			</label>
			<label class="text-xs text-surface-500">
				<span class="block">{m.domain()}</span>
				<select name="folder" class="select rounded-md text-sm">
					{#each data.folders as f}<option value={f.id}>{f.name}</option>{/each}
				</select>
			</label>
			<label class="text-xs text-surface-500">
				<span class="block">{m.file()}</span>
				<input name="file" type="file" required class="input rounded-md text-sm" />
			</label>
			<button class="btn btn-sm preset-filled-primary-500">
				<i class="fa-solid fa-upload mr-1"></i>{m.upload()}
			</button>
		</form>
	</section>

	<section class="card bg-surface-50-950 p-6">
		<div class="divide-y divide-surface-200-800">
			{#each data.documents as doc}
				<div class="flex items-center justify-between py-2">
					<div class="flex items-center gap-3">
						<i class="fa-solid fa-file text-surface-400"></i>
						<span class="font-medium">{doc.name}</span>
						<span class="text-xs text-surface-400">{humanSize(doc.size)}</span>
					</div>
					<div class="flex items-center gap-2">
						<a
							href={`/trust/documents/${doc.token}`}
							target="_blank"
							rel="noopener"
							class="btn btn-sm preset-tonal"
							aria-label={m.open()}><i class="fa-solid fa-arrow-up-right-from-square"></i></a
						>
						<form method="POST" action="?/delete" use:enhance>
							<input type="hidden" name="id" value={doc.id} />
							<button
								type="button"
								onclick={(e) => confirmDelete(e, doc.name)}
								class="btn btn-sm preset-tonal-error"
								aria-label={m.delete()}
								title={m.delete()}><i class="fa-solid fa-trash"></i></button
							>
						</form>
					</div>
				</div>
			{:else}
				<p class="py-2 text-sm text-surface-500">{m.noPublicDocuments()}</p>
			{/each}
		</div>
	</section>
</div>
