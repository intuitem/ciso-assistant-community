<script lang="ts">
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const TYPE_ORDER = ['policy', 'procedure', 'charter', 'record', 'other'];
	const TYPE_LABEL: Record<string, () => string> = {
		policy: m.policy,
		procedure: m.procedure,
		charter: m.charter,
		record: m.record,
		other: m.other
	};

	function typeLabel(t: string): string {
		return TYPE_LABEL[t] ? TYPE_LABEL[t]() : t;
	}

	function localeName(loc: string): string {
		return LOCALE_MAP[loc]?.name ?? loc.toUpperCase();
	}

	let grouped = $derived.by(() => {
		const g: Record<string, any[]> = {};
		for (const c of data.catalog ?? []) {
			(g[c.document_type] ??= []).push(c);
		}
		return TYPE_ORDER.filter((t) => g[t]?.length).map((t) => ({ type: t, items: g[t] }));
	});
</script>

<div class="p-4 space-y-8">
	<header class="flex items-center justify-between gap-3">
		<div class="flex items-center gap-3">
			<i class="fa-solid fa-book-open text-xl text-primary-500"></i>
			<h1 class="text-2xl font-bold">{m.documents()}</h1>
		</div>
		<a href="/document-containers" class="btn btn-sm variant-soft">
			<i class="fa-solid fa-table-list mr-2"></i>{m.manage()}
		</a>
	</header>

	{#if grouped.length === 0}
		<p class="text-surface-500">{m.noPublishedDocuments()}</p>
	{/if}

	{#each grouped as group (group.type)}
		<section class="space-y-3">
			<h2 class="text-lg font-semibold text-surface-700-300">{typeLabel(group.type)}</h2>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each group.items as doc (doc.id)}
					<div class="card space-y-3 border border-surface-200-800 p-4">
						<div class="flex items-start justify-between gap-2">
							<h3 class="font-semibold leading-tight">{doc.name || m.untitled()}</h3>
							<span class="badge variant-soft-primary shrink-0 text-xs">
								{typeLabel(doc.document_type)}
							</span>
						</div>
						{#if doc.folder}
							<p class="text-xs text-surface-500">
								<i class="fa-solid fa-folder mr-1"></i>{doc.folder.str}
							</p>
						{/if}
						<div class="flex flex-wrap gap-1.5 pt-1">
							{#each doc.languages as lang (lang.document_id)}
								<a
									href={`/documents/${doc.id}/read?doc=${lang.document_id}`}
									class="chip variant-soft text-xs hover:variant-filled-primary"
									title={`${localeName(lang.locale)} · v${lang.version_number}`}
								>
									{localeName(lang.locale)} · v{lang.version_number}
								</a>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/each}
</div>
