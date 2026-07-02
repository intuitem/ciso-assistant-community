<script lang="ts">
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import { documentTypeLabel, documentTypeIcon } from '$lib/utils/documentTypes';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import DocumentReferencesPanel from '$lib/components/DocumentEditor/DocumentReferencesPanel.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	function localeName(loc: string): string {
		return LOCALE_MAP[loc]?.name ?? loc.toUpperCase();
	}

	// Only languages with a published revision are readable.
	let publishedDocs = $derived(
		(data.docs ?? []).filter((d: any) => d.current_revision?.status === 'published')
	);

	let docType = $derived(data.container?.document_type ?? 'other');
	let isUploaded = $derived(data.revision?.source === 'uploaded');
	let fileUrl = $derived(
		data.revision?.id ? `/documents/${data.container?.id}/read/file?rev=${data.revision.id}` : ''
	);
	let isPdf = $derived((data.revision?.file ?? '').toLowerCase().endsWith('.pdf'));
</script>

<div class="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
	<a
		href="/documents"
		class="inline-flex items-center gap-1.5 text-sm text-surface-500 transition-colors hover:text-primary-500"
	>
		<i class="fa-solid fa-arrow-left"></i>{m.documents()}
	</a>

	<!-- Document header -->
	<header
		class="relative overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 pl-7"
	>
		<span class="absolute inset-y-0 left-0 w-1.5 bg-primary-500"></span>
		<div class="space-y-4">
			<div class="flex items-start gap-4">
				<div
					class="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-xl text-primary-500 ring-1 ring-primary-500/20"
				>
					<i class="fa-solid {documentTypeIcon(docType)}"></i>
				</div>
				<div class="min-w-0 flex-1 space-y-2">
					<h1 class="text-2xl font-bold leading-tight tracking-tight">
						{data.container?.name || m.untitled()}
					</h1>
					<div class="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-surface-500">
						<span class="font-semibold uppercase tracking-wide text-primary-500">
							{documentTypeLabel(docType)}
						</span>
						{#if data.container?.folder}
							<span class="text-surface-300-700">·</span>
							<span class="inline-flex items-center gap-1">
								<i class="fa-solid fa-folder-tree opacity-70"></i>{data.container.folder.str}
							</span>
						{/if}
						{#if data.selected?.current_revision}
							<span class="text-surface-300-700">·</span>
							<span class="inline-flex items-center gap-1 tabular-nums">
								<i class="fa-solid fa-code-branch opacity-70"></i>v{data.selected.current_revision
									.version_number}
							</span>
						{/if}
					</div>
				</div>
			</div>

			{#if publishedDocs.length > 1}
				<div class="flex flex-wrap items-center gap-1.5 border-t border-surface-200-800 pt-4">
					<span class="mr-1 text-[10px] font-semibold uppercase tracking-wider text-surface-400">
						{m.language()}
					</span>
					{#each publishedDocs as d (d.id)}
						<a
							href={`?doc=${d.id}`}
							class="rounded-md border px-2.5 py-1 text-xs font-medium transition-colors {d.id ===
							data.selected?.id
								? 'border-primary-500 bg-primary-500 text-white'
								: 'border-surface-200-800 bg-surface-50-950 text-surface-600-400 hover:border-primary-500/50 hover:text-primary-500'}"
						>
							{localeName(d.locale)}
						</a>
					{/each}
				</div>
			{/if}
		</div>
	</header>

	{#if isUploaded && fileUrl}
		<div class="space-y-4">
			<a href={fileUrl} target="_blank" rel="noopener" class="btn btn-sm variant-filled-primary">
				<i class="fa-solid fa-download mr-2"></i>{m.download()}
			</a>
			{#if isPdf}
				<iframe
					src={fileUrl}
					title={data.container?.name}
					class="h-[75vh] w-full rounded-xl border border-surface-200-800 shadow-sm"
				></iframe>
			{/if}
		</div>
	{:else if data.content}
		<article
			class="rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 shadow-sm sm:p-10"
		>
			<div class="prose max-w-none dark:prose-invert">
				<MarkdownRenderer content={data.content} />
			</div>
		</article>
	{:else}
		<div
			class="flex flex-col items-center gap-3 rounded-xl border border-dashed border-surface-300-700 py-16 text-surface-500"
		>
			<i class="fa-solid fa-file-circle-xmark text-3xl opacity-50"></i>
			<p class="font-medium">{m.noPublishedDocuments()}</p>
		</div>
	{/if}

	<DocumentReferencesPanel refs={data.refs} />
</div>
