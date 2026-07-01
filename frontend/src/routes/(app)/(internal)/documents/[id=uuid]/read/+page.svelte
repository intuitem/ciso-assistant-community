<script lang="ts">
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	function localeName(loc: string): string {
		return LOCALE_MAP[loc]?.name ?? loc.toUpperCase();
	}

	// Only languages with a published revision are readable.
	let publishedDocs = $derived(
		(data.docs ?? []).filter((d: any) => d.current_revision?.status === 'published')
	);
</script>

<div class="mx-auto max-w-4xl space-y-6 p-4">
	<header class="space-y-3 border-b border-surface-200-800 pb-4">
		<a href="/documents" class="text-sm text-primary-500 hover:underline">
			<i class="fa-solid fa-arrow-left mr-1"></i>{m.documents()}
		</a>
		<div class="flex items-start justify-between gap-3">
			<h1 class="text-2xl font-bold">{data.container?.name || m.untitled()}</h1>
			{#if data.selected?.current_revision}
				<span class="badge variant-soft-primary shrink-0 text-xs">
					v{data.selected.current_revision.version_number}
				</span>
			{/if}
		</div>

		{#if publishedDocs.length > 1}
			<div class="flex flex-wrap gap-1.5">
				{#each publishedDocs as d (d.id)}
					<a
						href={`?doc=${d.id}`}
						class="chip text-xs {d.id === data.selected?.id
							? 'variant-filled-primary'
							: 'variant-soft'}"
					>
						{localeName(d.locale)}
					</a>
				{/each}
			</div>
		{/if}
	</header>

	{#if data.content}
		<article class="prose max-w-none dark:prose-invert">
			<MarkdownRenderer content={data.content} />
		</article>
	{:else}
		<p class="text-surface-500">{m.noPublishedDocuments()}</p>
	{/if}
</div>
