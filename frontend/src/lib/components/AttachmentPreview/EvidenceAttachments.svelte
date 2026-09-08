<script lang="ts">
	import AttachmentPreview from './AttachmentPreview.svelte';
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { enhance } from '$app/forms';
	import type { EvidenceAttachment } from '$lib/utils/evidence-files';
	let {
		attachments = [],
		canEdit = false
	}: { attachments?: EvidenceAttachment[]; canEdit?: boolean } = $props();
	let selectedId: string | undefined = $state();
	const selected = $derived(attachments.find((file) => file.id === selectedId) ?? attachments[0]);
	const endpoint = (file: EvidenceAttachment) =>
		`/evidence-revisions/${file.revision_id}/attachments/${file.id}`;
	let error = $state('');
	let pending = $state(false);
</script>

{#if attachments.length}
	<section class="card mt-8 p-6 bg-surface-50-950 space-y-4 shadow-lg" aria-label={m.attachments()}>
		<h4 class="h4 font-semibold">{m.attachments()} ({attachments.length}/10)</h4>
		{#if error}<p class="text-error-500" role="alert">{error}</p>{/if}
		<ul class="space-y-2">
			{#each attachments as file (file.id)}
				<li class="flex flex-wrap items-center gap-2">
					<button
						type="button"
						class="btn flex-1 min-w-0 justify-start text-left"
						class:preset-tonal-primary={selected?.id === file.id}
						aria-pressed={selected?.id === file.id}
						onclick={() => (selectedId = file.id)}
					>
						<span class="break-all">{file.filename}</span><span class="shrink-0 text-sm"
							>{file.size ?? ''}</span
						>
					</button>
					<a
						class="btn preset-filled-primary-500"
						href={endpoint(file)}
						download
						aria-label={`${m.download()}: ${file.filename}`}><i class="fa-solid fa-download"></i></a
					>
					{#if canEdit}
						<form
							method="POST"
							action="?/deleteFile"
							use:enhance={({ cancel }) => {
								if (!confirm(`${m.confirmModalMessage()}: ${file.filename}?`)) {
									cancel();
									return;
								}
								pending = true;
								return async ({ result }) => {
									pending = false;
									if (result.type === 'success') {
										error = '';
										await invalidateAll();
									} else error = m.evidenceFileDeleteFailed();
								};
							}}
						>
							<input type="hidden" name="revisionId" value={file.revision_id} />
							<input type="hidden" name="fileId" value={file.id} />
							<button
								type="submit"
								disabled={pending}
								class="btn preset-filled-tertiary-500"
								aria-label={`${m.delete()}: ${file.filename}`}
								><i class="fa-solid fa-trash"></i></button
							>
						</form>
					{/if}
				</li>
			{/each}
		</ul>
		{#if selected}
			{#key selected.id}<AttachmentPreview
					endpoint={endpoint(selected)}
					filename={selected.filename}
				/>{/key}
		{/if}
	</section>
{/if}
