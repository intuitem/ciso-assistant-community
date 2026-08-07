<script lang="ts">
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import { documentTypeLabel, documentTypeIcon } from '$lib/utils/documentTypes';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let t = $derived(data.template);

	const localeName = (loc: string) => LOCALE_MAP[loc]?.name ?? loc.toUpperCase();
</script>

<div class="mx-auto max-w-4xl space-y-6 p-4 sm:p-6">
	<a
		href="/document-templates"
		class="inline-flex items-center gap-1.5 text-sm text-surface-500 transition-colors hover:text-primary-500"
	>
		<i class="fa-solid fa-arrow-left"></i>{m.documentTemplates()}
	</a>

	<header
		class="relative overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 pl-7"
	>
		<span class="absolute inset-y-0 left-0 w-1.5 bg-primary-500"></span>
		<div class="flex items-start justify-between gap-4">
			<div class="flex min-w-0 items-start gap-4">
				<div
					class="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-xl text-primary-500 ring-1 ring-primary-500/20"
				>
					<i class="fa-solid {documentTypeIcon(t.document_type)}"></i>
				</div>
				<div class="min-w-0 space-y-2">
					<h1 class="text-2xl font-bold leading-tight tracking-tight">{t.name}</h1>
					<div class="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs text-surface-500">
						<span class="font-semibold uppercase tracking-wide text-primary-500">
							{documentTypeLabel(t.document_type)}
						</span>
						<span class="text-surface-300-700">·</span>
						<span class="inline-flex items-center gap-1">
							<i class="fa-solid fa-language opacity-70"></i>{localeName(t.locale)}
						</span>
						{#if t.folder}
							<span class="text-surface-300-700">·</span>
							<span class="inline-flex items-center gap-1">
								<i class="fa-solid fa-folder-tree opacity-70"></i>{t.folder.str}
							</span>
						{/if}
						<span class="text-surface-300-700">·</span>
						<span class="inline-flex items-center gap-1 font-mono">
							<i class="fa-solid fa-hashtag opacity-70"></i>{t.ref_id}
						</span>
						{#if t.builtin}
							<span class="badge preset-tonal-surface text-xs">{m.builtin()}</span>
						{/if}
					</div>
					{#if t.description}
						<p class="text-sm text-surface-600-400">{t.description}</p>
					{/if}
				</div>
			</div>
			{#if !t.builtin}
				<a
					href="/document-templates/{t.id}/edit?next={encodeURIComponent(
						`/document-templates/${t.id}`
					)}"
					class="btn btn-sm variant-filled-primary shrink-0"
				>
					<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
				</a>
			{/if}
		</div>
	</header>

	{#if t.content}
		<article
			class="rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 shadow-sm sm:p-10"
		>
			<div class="prose max-w-none dark:prose-invert">
				<MarkdownRenderer content={t.content} />
			</div>
		</article>
	{:else}
		<p class="text-surface-500">—</p>
	{/if}
</div>
