<script lang="ts">
	import { run } from 'svelte/legacy';

	import { onMount, onDestroy } from 'svelte';
	import { m } from '$paraglide/messages';
	import { attachmentCache, generateAttachmentCacheKey } from '$lib/stores/attachmentCache';

	interface Props {
		cell: any;
		meta: any;
	}

	let { cell, meta }: Props = $props();

	interface Attachment {
		type: string;
		url: string;
		fileExists: boolean;
	}

	let attachment: Attachment | undefined = $state();
	let containerElement: HTMLElement | undefined = $state();
	let isVisible = $state(false);
	let observer: IntersectionObserver | undefined;
	let cacheKey = $state('');

	const fetchAttachment = async () => {
		// Generate cache key
		cacheKey = generateAttachmentCacheKey(meta.id, meta.attachment);

		// Check cache first
		if (attachmentCache.has(cacheKey)) {
			const cached = attachmentCache.get(cacheKey);
			if (cached) {
				return cached;
			}
		}

		// Fetch from server if not in cache
		try {
			const res = await fetch(
				`/${meta.evidence ? 'evidence-revisions' : 'evidences'}/${meta.id}/attachment`
			);
			if (!res.ok) {
				const miss = { type: '', url: '', fileExists: false } satisfies Attachment;
				attachmentCache.set(cacheKey, miss);
				return miss;
			}
			const blob = await res.blob();
			const result = {
				type: blob.type,
				url: URL.createObjectURL(blob),
				fileExists: true
			} satisfies Attachment;
			attachmentCache.set(cacheKey, result);
			return result;
		} catch (err) {
			if ((err as any)?.name === 'AbortError') {
				const miss = { type: '', url: '', fileExists: false } satisfies Attachment;
				return miss;
			}
			const miss = { type: '', url: '', fileExists: false } satisfies Attachment;
			attachmentCache.set(cacheKey, miss);
			return miss;
		}
	};

	let mounted = $state(false);
	onMount(() => {
		mounted = true;

		// Set up Intersection Observer for lazy loading
		if (containerElement && meta.attachment) {
			observer = new IntersectionObserver(
				(entries) => {
					entries.forEach((entry) => {
						if (entry.isIntersecting && !isVisible) {
							isVisible = true;
							// Fetch attachment when element becomes visible
							fetchAttachment().then((_attachment) => {
								attachment = _attachment;
							});
							// Disconnect after first load
							observer?.disconnect();
						}
					});
				},
				{
					rootMargin: '50px' // Start loading slightly before element is visible
				}
			);
			observer.observe(containerElement);
		}
	});

	onDestroy(() => {
		// Clean up observer
		if (observer) {
			observer.disconnect();
		}
		// Note: We do NOT revoke blob URLs here because the attachmentCache
		// is shared across multiple components. The cache itself handles
		// URL revocation when URLs are replaced or when cache.clear() is called.
		// Revoking URLs here would break other components using the same attachment.
	});

	run(() => {
		if (mounted && meta.attachment) {
			// Check cache first when meta changes
			const key = generateAttachmentCacheKey(meta.id, meta.attachment);
			if (attachmentCache.has(key)) {
				const cached = attachmentCache.get(key);
				if (cached) {
					attachment = cached;
					return;
				}
			}

			// If visible, fetch immediately
			if (isVisible) {
				fetchAttachment().then((_attachment) => {
					attachment = _attachment;
				});
			}
		} else {
			attachment = undefined;
		}
	});

	let display = $state(false);
	const wrapperClasses =
		'fixed w-full h-full inset-0 flex justify-center items-center backdrop-blur-sm backdrop-brightness-40 z-999';
	const imageElementClasses = 'w-[90%] h-[90%]';
	const embedElementClasses = 'w-[50%] h-[90%]';
</script>

{#snippet displayPreview(att: Attachment)}
	<div
		role="button"
		tabindex="0"
		class={display ? wrapperClasses : 'relative cursor-zoom-in'}
		onclick={(event) => {
			display = !display;
			event.stopPropagation();
		}}
		onkeydown={(event) => {
			if ((display && event.key === 'Escape') || event.key === 'Tab') {
				display = !display;
			}
		}}
	>
		{#if att.type.startsWith('image')}
			<img
				src={att.url}
				alt="attachment"
				class="h-24 object-contain {display ? imageElementClasses : ''}"
			/>
		{:else if att.type === 'application/pdf'}
			{#if !display}
				<!-- This div prevents the <embed> element from stopping the click event propagation. -->
				<div class="absolute w-full h-full top-0 left-0"></div>
			{/if}
			<embed
				src={att.url}
				type="application/pdf"
				class="h-24 object-contain {display ? embedElementClasses : ''}"
			/>
		{/if}
	</div>
{/snippet}

<div bind:this={containerElement}>
	{#if cell}
		{#if attachment}
			{#if attachment.type.startsWith('image') || attachment.type === 'application/pdf'}
				{@render displayPreview(attachment)}
			{:else if !attachment.fileExists}
				<p class="text-error-500 font-bold">{m.couldNotFindAttachmentMessage()}</p>
			{:else}
				<p>{m.NoPreviewMessage()}</p>
			{/if}
		{:else}
			<span data-testid="loading-field">
				{m.loading()}...
			</span>
		{/if}
	{/if}
</div>
