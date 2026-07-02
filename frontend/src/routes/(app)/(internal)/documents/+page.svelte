<script lang="ts">
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const TYPES = [
		{ key: 'policy', label: m.policy, icon: 'fa-shield-halved' },
		{ key: 'procedure', label: m.procedure, icon: 'fa-list-check' },
		{ key: 'charter', label: m.charter, icon: 'fa-scroll' },
		{ key: 'record', label: m.record, icon: 'fa-box-archive' },
		{ key: 'meeting_minutes', label: m.meetingMinutes, icon: 'fa-users' },
		{ key: 'other', label: m.other, icon: 'fa-file-lines' }
	];
	const TYPE_META: Record<string, { label: () => string; icon: string }> = Object.fromEntries(
		TYPES.map((t) => [t.key, { label: t.label, icon: t.icon }])
	);

	let query = $state('');
	let selectedTypes = $state<Set<string>>(new Set());

	const localeName = (loc: string) => LOCALE_MAP[loc]?.name ?? loc.toUpperCase();
	const typeLabel = (t: string) => TYPE_META[t]?.label() ?? t;
	const typeIcon = (t: string) => TYPE_META[t]?.icon ?? 'fa-file-lines';
	const readHref = (doc: any, lang: any) => `/documents/${doc.id}/read?doc=${lang.document_id}`;

	let catalog = $derived((data.catalog ?? []) as any[]);

	let typeCounts = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const c of catalog) counts[c.document_type] = (counts[c.document_type] ?? 0) + 1;
		return counts;
	});

	let filtered = $derived.by(() => {
		const q = query.trim().toLowerCase();
		return catalog.filter((c) => {
			if (selectedTypes.size && !selectedTypes.has(c.document_type)) return false;
			if (q) {
				const hay = `${c.name ?? ''} ${c.folder?.str ?? ''}`.toLowerCase();
				if (!hay.includes(q)) return false;
			}
			return true;
		});
	});

	let grouped = $derived.by(() => {
		const g: Record<string, any[]> = {};
		for (const c of filtered) (g[c.document_type] ??= []).push(c);
		return TYPES.map((t) => t.key)
			.filter((k) => g[k]?.length)
			.map((k) => ({ type: k, items: g[k] }));
	});

	function toggleType(t: string) {
		const next = new Set(selectedTypes);
		if (next.has(t)) next.delete(t);
		else next.add(t);
		selectedTypes = next;
	}
</script>

<div class="space-y-6 p-4">
	<!-- Header -->
	<header class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex items-center gap-3">
			<i class="fa-solid fa-book-open text-2xl text-primary-500"></i>
			<div>
				<h1 class="text-2xl font-bold">{m.documents()}</h1>
				<p class="text-sm text-surface-500">
					{filtered.length}{filtered.length !== catalog.length ? ` / ${catalog.length}` : ''}
				</p>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<a href="/documents/upload" class="btn btn-sm variant-filled-primary">
				<i class="fa-solid fa-upload mr-2"></i>{m.uploadDocument()}
			</a>
			<a href="/document-containers" class="btn btn-sm variant-soft">
				<i class="fa-solid fa-table-list mr-2"></i>{m.manage()}
			</a>
		</div>
	</header>

	<!-- Toolbar: search + type filters -->
	<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
		<div class="relative w-full sm:max-w-xs">
			<i
				class="fa-solid fa-magnifying-glass pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-surface-400"
			></i>
			<input type="search" bind:value={query} placeholder={m.search()} class="input w-full pl-9" />
		</div>
		<div class="flex flex-wrap gap-1.5">
			{#each TYPES as t (t.key)}
				{#if typeCounts[t.key]}
					<button
						type="button"
						class="chip text-xs {selectedTypes.has(t.key)
							? 'variant-filled-primary'
							: 'variant-soft'}"
						onclick={() => toggleType(t.key)}
					>
						<i class="fa-solid {t.icon} mr-1"></i>{t.label()} · {typeCounts[t.key]}
					</button>
				{/if}
			{/each}
		</div>
	</div>

	<!-- Tiles -->
	{#if grouped.length === 0}
		<div class="flex flex-col items-center gap-2 py-16 text-surface-500">
			<i class="fa-solid fa-folder-open text-3xl opacity-60"></i>
			<p>{m.noPublishedDocuments()}</p>
		</div>
	{/if}

	{#each grouped as group (group.type)}
		<section class="space-y-3">
			<h2
				class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-surface-500"
			>
				<i class="fa-solid {typeIcon(group.type)}"></i>{typeLabel(group.type)}
				<span class="text-surface-400">({group.items.length})</span>
			</h2>
			<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
				{#each group.items as doc (doc.id)}
					<div
						class="card flex flex-col gap-3 border border-surface-200-800 p-4 transition hover:border-primary-500 hover:shadow-md"
					>
						<div class="flex items-start gap-3">
							<div
								class="grid h-9 w-9 shrink-0 place-items-center rounded bg-primary-500/10 text-primary-500"
							>
								<i class="fa-solid {typeIcon(doc.document_type)}"></i>
							</div>
							<a
								href={readHref(doc, doc.languages[0])}
								class="font-semibold leading-tight hover:text-primary-600 hover:underline"
							>
								{doc.name || m.untitled()}
							</a>
						</div>
						{#if doc.folder}
							<p class="text-xs text-surface-500">
								<i class="fa-solid fa-folder mr-1"></i>{doc.folder.str}
							</p>
						{/if}
						<div class="mt-auto flex flex-wrap gap-1.5 pt-1">
							{#each doc.languages as lang (lang.document_id)}
								<a
									href={readHref(doc, lang)}
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
