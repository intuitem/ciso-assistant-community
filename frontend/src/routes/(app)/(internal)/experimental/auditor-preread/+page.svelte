<script lang="ts">
	import { safeTranslate } from '#lib/utils/i18n.js';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let query = $state('');
	const audits = $derived(
		data.audits.filter((a: any) =>
			[a.name, a.folder?.str, a.perimeter?.str]
				.join(' ')
				.toLowerCase()
				.includes(query.trim().toLowerCase())
		)
	);
</script>

<div class="p-4 md:p-6 flex flex-col gap-5">
	<header class="flex flex-col gap-2 max-w-3xl">
		<span class="text-xs uppercase tracking-wider text-primary-600-400 font-semibold">
			<i class="fa-solid fa-user-tie mr-1"></i>Experimental
		</span>
		<h1 class="text-2xl font-semibold">Auditor pre-read</h1>
		<p class="text-surface-600-400">
			Get ahead of the certification auditor. For each requirement: what they will ask, which
			records they will request, how they will sample and who they will interview, set against the
			evidence already in the audit.
		</p>
		<ul class="flex flex-wrap gap-x-5 gap-y-1 text-sm text-surface-600-400">
			<li><i class="fa-solid fa-list-check mr-1.5"></i>Readiness per requirement</li>
			<li><i class="fa-solid fa-folder-open mr-1.5"></i>Evidence request list</li>
			<li><i class="fa-solid fa-people-group mr-1.5"></i>Interview plan</li>
		</ul>
	</header>

	{#if !data.frameworks.length}
		<div class="card preset-tonal-warning p-4 flex gap-3 items-start">
			<i class="fa-solid fa-book mt-1"></i>
			<p>
				ISO/IEC 27001:2022 is not loaded. Load it from the
				<a class="anchor" href="/libraries">libraries</a>, then create an audit on it.
			</p>
		</div>
	{:else if !data.audits.length}
		<div
			class="card border border-dashed border-surface-300-700 p-8 text-center text-surface-600-400 flex flex-col gap-2 items-center"
		>
			<i class="fa-solid fa-clipboard-question text-3xl"></i>
			<p>No ISO/IEC 27001:2022 audit you can view yet.</p>
			<a class="btn btn-sm preset-filled-primary-500" href="/compliance-assessments">Go to audits</a
			>
		</div>
	{:else}
		<div class="flex items-center gap-3">
			<label class="relative grow max-w-sm">
				<span class="sr-only">Search audits</span>
				<i
					class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-500 text-sm"
				></i>
				<input
					class="input pl-9 w-full"
					type="search"
					placeholder="Search audits, domains, perimeters"
					bind:value={query}
				/>
			</label>
			<span class="text-sm text-surface-600-400 tabular-nums"
				>{audits.length} ISO/IEC 27001:2022 audit{audits.length === 1 ? '' : 's'}</span
			>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each audits as audit (audit.id)}
				<a
					href="/experimental/auditor-preread/{audit.id}"
					class="card border border-surface-200-800 p-4 flex flex-col gap-3 hover:border-primary-500 hover:shadow-md transition group"
				>
					<div class="flex items-start justify-between gap-3">
						<h2 class="font-semibold leading-snug group-hover:text-primary-600-400">
							{audit.name}
						</h2>
						{#if audit.status}
							<span class="badge preset-tonal-surface shrink-0">{safeTranslate(audit.status)}</span>
						{/if}
					</div>
					<dl class="text-sm grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-surface-600-400">
						<dt><i class="fa-solid fa-sitemap" title="Domain"></i></dt>
						<dd class="truncate">{audit.folder?.str ?? '—'}</dd>
						<dt><i class="fa-solid fa-cubes" title="Perimeter"></i></dt>
						<dd class="truncate">{audit.perimeter?.str?.split('/').pop() ?? 'No perimeter'}</dd>
					</dl>
					<span class="mt-auto text-sm text-primary-600-400 font-medium">
						Open pre-read<i class="fa-solid fa-arrow-right ml-1.5"></i>
					</span>
				</a>
			{:else}
				<p class="text-sm text-surface-600-400">No audit matches “{query}”.</p>
			{/each}
		</div>
	{/if}
</div>
