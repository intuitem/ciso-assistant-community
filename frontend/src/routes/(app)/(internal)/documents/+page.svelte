<script lang="ts">
	import { m } from '$paraglide/messages';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import {
		DOCUMENT_TYPES as TYPES,
		documentTypeLabel as typeLabel,
		documentTypeIcon as typeIcon
	} from '$lib/utils/documentTypes';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let query = $state('');
	let selectedTypes = $state<Set<string>>(new Set());

	const localeName = (loc: string) => LOCALE_MAP[loc]?.name ?? loc.toUpperCase();
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

	let hasFilters = $derived(query.trim().length > 0 || selectedTypes.size > 0);

	function toggleType(t: string) {
		const next = new Set(selectedTypes);
		if (next.has(t)) next.delete(t);
		else next.add(t);
		selectedTypes = next;
	}

	function clearFilters() {
		query = '';
		selectedTypes = new Set();
	}
</script>

<div class="doc-library mx-auto max-w-7xl space-y-8 p-4 sm:p-6">
	<!-- Masthead -->
	<header
		class="relative overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950"
	>
		<div
			class="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-primary-500/10 blur-3xl"
		></div>
		<div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-primary-500/40"></div>
		<div class="relative flex flex-wrap items-end justify-between gap-4 p-6">
			<div class="flex items-center gap-4">
				<div
					class="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-2xl text-primary-500 ring-1 ring-primary-500/20"
				>
					<i class="fa-solid fa-book-open"></i>
				</div>
				<div class="flex items-center gap-3">
					<h1 class="text-3xl font-bold leading-none tracking-tight">{m.documents()}</h1>
					<span
						class="rounded-full bg-primary-500/10 px-2.5 py-1 text-sm font-semibold tabular-nums text-primary-500"
					>
						{#if hasFilters}{filtered.length}&thinsp;/&thinsp;{catalog.length}{:else}{catalog.length}{/if}
					</span>
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
		</div>
	</header>

	<!-- Toolbar: search + type filters -->
	<div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
		<div class="relative w-full lg:max-w-sm">
			<i
				class="fa-solid fa-magnifying-glass pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-surface-400"
			></i>
			<input
				type="search"
				bind:value={query}
				placeholder={m.search()}
				class="input w-full rounded-lg pl-10"
			/>
		</div>
		<div class="flex flex-wrap items-center gap-1.5">
			{#each TYPES as t (t.key)}
				{#if typeCounts[t.key]}
					<button
						type="button"
						aria-pressed={selectedTypes.has(t.key)}
						class="group inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all duration-150 {selectedTypes.has(
							t.key
						)
							? 'border-primary-500 bg-primary-500 text-white shadow-sm'
							: 'border-surface-200-800 bg-surface-50-950 text-surface-600-400 hover:border-primary-500/50 hover:text-primary-500'}"
						onclick={() => toggleType(t.key)}
					>
						<i class="fa-solid {t.icon} text-[10px] opacity-80"></i>
						{t.label()}
						<span
							class="rounded-full px-1.5 text-[10px] tabular-nums {selectedTypes.has(t.key)
								? 'bg-white/25'
								: 'bg-surface-200-700'}">{typeCounts[t.key]}</span
						>
					</button>
				{/if}
			{/each}
			{#if hasFilters}
				<button
					type="button"
					class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs text-surface-500 transition-colors hover:text-error-500"
					onclick={clearFilters}
				>
					<i class="fa-solid fa-xmark"></i>{m.clearFilters()}
				</button>
			{/if}
		</div>
	</div>

	<!-- Empty state -->
	{#if grouped.length === 0}
		<div
			class="flex flex-col items-center gap-3 rounded-xl border border-dashed border-surface-300-700 py-20 text-surface-500"
		>
			<i class="fa-solid fa-folder-open text-4xl opacity-50"></i>
			<p class="font-medium">{m.noPublishedDocuments()}</p>
			{#if hasFilters}
				<button type="button" class="btn btn-sm variant-soft" onclick={clearFilters}>
					<i class="fa-solid fa-rotate-left mr-2"></i>{m.clearFilters()}
				</button>
			{/if}
		</div>
	{/if}

	<!-- Shelves -->
	{#each grouped as group (group.type)}
		<section class="space-y-4">
			<div class="flex items-center gap-3">
				<span
					class="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-primary-500/10 text-xs text-primary-500"
				>
					<i class="fa-solid {typeIcon(group.type)}"></i>
				</span>
				<h2 class="text-sm font-semibold uppercase tracking-widest text-surface-600-400">
					{typeLabel(group.type)}
				</h2>
				<span class="text-xs tabular-nums text-surface-400">{group.items.length}</span>
				<div class="h-px flex-1 bg-gradient-to-r from-surface-200-800 to-transparent"></div>
			</div>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
				{#each group.items as doc, i (doc.id)}
					<div
						class="doc-tile group relative flex min-h-36 flex-col gap-2.5 overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950 p-4 pl-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary-500/40 hover:shadow-lg"
						style="animation-delay: {Math.min(i, 12) * 35}ms"
					>
						<!-- document spine -->
						<span
							class="absolute inset-y-0 left-0 w-1 bg-primary-500/30 transition-all duration-200 group-hover:w-1.5 group-hover:bg-primary-500"
						></span>

						<a
							href={readHref(doc, doc.languages[0])}
							class="line-clamp-3 text-base font-semibold leading-snug tracking-tight transition-colors duration-150 group-hover:text-primary-600 focus:outline-none focus-visible:underline"
						>
							{doc.name || m.untitled()}
							<span class="absolute inset-0" aria-hidden="true"></span>
						</a>

						{#if doc.folder}
							<p class="flex items-center gap-1.5 truncate text-xs text-surface-500">
								<i class="fa-solid fa-folder-tree opacity-70"></i>{doc.folder.str}
							</p>
						{/if}

						<div
							class="relative z-10 mt-auto flex flex-wrap items-center gap-1.5 border-t border-surface-200-800 pt-3"
						>
							{#each doc.languages as lang (lang.document_id)}
								<a
									href={readHref(doc, lang)}
									class="inline-flex items-center gap-1 rounded-md border border-surface-200-800 bg-surface-100-900 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-surface-600-400 transition-colors hover:border-primary-500 hover:bg-primary-500 hover:text-white"
									title={`${localeName(lang.locale)} · v${lang.version_number}`}
								>
									<span class="uppercase">{lang.locale}</span>
									<span class="opacity-60">v{lang.version_number}</span>
								</a>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/each}
</div>

<style>
	.doc-tile {
		animation: tile-in 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
	}

	@keyframes tile-in {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.doc-tile {
			animation: none;
		}
	}
</style>
