<script lang="ts">
	import AttachmentPreview from '#lib/components/AttachmentPreview/AttachmentPreview.svelte';
	import { m } from '#paraglide/messages.js';
	import type { Revision } from './types';

	let { revision, loading }: { revision: Revision | undefined; loading: boolean } = $props();

	const host = $derived.by(() => {
		try {
			return revision?.link ? new URL(revision.link).hostname : '';
		} catch {
			return revision?.link ?? '';
		}
	});
</script>

<div
	class="h-full min-h-0 overflow-auto rounded-lg bg-surface-100-900 p-4 [&_img]:max-w-full [&_img]:max-h-full [&_img]:object-contain [&_img]:mx-auto [&_img]:rounded [&_img]:shadow-md [&_embed]:h-full"
>
	{#if loading}
		<div class="h-full grid place-items-center text-surface-600-400">
			<i class="fa-solid fa-spinner fa-spin text-2xl" aria-label={m.loading()}></i>
		</div>
	{:else if revision?.attachment}
		{#key revision.id}
			<AttachmentPreview
				endpoint={`/evidence-revisions/${revision.id}/attachment`}
				filename={revision.attachment}
			/>
		{/key}
	{:else if revision?.link}
		<div class="h-full grid place-items-center p-6">
			<a
				class="card preset-filled-surface-50-950 flex items-center gap-4 p-5 w-full max-w-lg shadow-sm hover:shadow-md transition-shadow"
				href={revision.link}
				target="_blank"
				rel="noopener noreferrer"
			>
				<span class="grid place-items-center size-12 rounded-full bg-primary-100-900 shrink-0">
					<i class="fa-solid fa-link text-primary-600-400 text-lg"></i>
				</span>
				<span class="min-w-0 grow">
					<span class="block font-semibold truncate">{host}</span>
					<span class="block text-xs text-surface-600-400 truncate">{revision.link}</span>
				</span>
				<i class="fa-solid fa-arrow-up-right-from-square text-surface-500"></i>
			</a>
		</div>
	{:else}
		<div class="h-full grid place-items-center text-surface-600-400 text-sm">
			<p><i class="fa-regular fa-file mr-2"></i>{m.reviewNoContent()}</p>
		</div>
	{/if}
</div>
