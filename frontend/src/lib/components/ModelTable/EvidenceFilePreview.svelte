<script lang="ts">
	import { onMount } from 'svelte';
	import * as m from '$paraglide/messages';

	export let cell: any;
	export let meta: any;

	interface Attachment {
		type: string;
		url: string;
	}

	let attachment: Attachment | undefined;

	onMount(async () => {
		const fetchAttachment = async () => {
			const res = await fetch(`/evidences/${meta.id}/attachment`);
			const blob = await res.blob();
			return { type: blob.type, url: URL.createObjectURL(blob) };
		};
		attachment = meta.attachment ? await fetchAttachment() : undefined;
	});
</script>

{#if cell}
	{#if attachment}
		{#if attachment.type.startsWith('image')}
			<img src={attachment.url} alt="attachment" class="h-24" />
		{:else if attachment.type === 'application/pdf'}
			<embed src={attachment.url} type="application/pdf" class="h-24" />
		{/if}
	{:else}
		<span data-testid="loading-field">
			{m.loading()}...
		</span>
	{/if}
{/if}
