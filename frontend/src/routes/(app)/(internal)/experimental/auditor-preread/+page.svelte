<script lang="ts">
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let query = $state('');
	const audits = $derived(
		data.audits.filter((a: any) =>
			[a.name, a.framework, a.folder?.str, a.perimeter?.str]
				.join(' ')
				.toLowerCase()
				.includes(query.trim().toLowerCase())
		)
	);
</script>

<div class="p-4 md:p-6 flex flex-col gap-5">
	<header class="flex flex-col gap-2 max-w-3xl">
		<span class="text-xs uppercase tracking-wider text-primary-600-400 font-semibold">
			<i class="fa-solid fa-user-tie mr-1"></i>{m.experimental()}
		</span>
		<h1 class="text-2xl font-semibold">{m.prereadTitle()}</h1>
		<p class="text-surface-600-400">
			{m.prereadIntro()}
		</p>
		<ul class="flex flex-wrap gap-x-5 gap-y-1 text-sm text-surface-600-400">
			<li><i class="fa-solid fa-list-check mr-1.5"></i>{m.prereadReadinessPerRequirement()}</li>
			<li><i class="fa-solid fa-folder-open mr-1.5"></i>{m.prereadRequestList()}</li>
			<li><i class="fa-solid fa-people-group mr-1.5"></i>{m.prereadInterviewPlan()}</li>
		</ul>
	</header>

	{#if !data.audits.length}
		<div
			class="card border border-dashed border-surface-300-700 p-8 text-center text-surface-600-400 flex flex-col gap-2 items-center"
		>
			<i class="fa-solid fa-clipboard-question text-3xl"></i>
			<p>
				{m.prereadNoAudit()}
			</p>
			<a class="btn btn-sm preset-filled-primary-500" href="/compliance-assessments"
				>{m.prereadGoToAudits()}</a
			>
		</div>
	{:else}
		<div class="flex items-center gap-3">
			<label class="relative grow max-w-sm">
				<span class="sr-only">{m.prereadSearchAudits()}</span>
				<i
					class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-surface-500 text-sm"
				></i>
				<input
					class="input pl-9 w-full"
					type="search"
					placeholder={m.prereadSearchAuditsPlaceholder()}
					bind:value={query}
				/>
			</label>
			<span class="text-sm text-surface-600-400 tabular-nums"
				>{m.prereadAuditCount({ count: audits.length })}</span
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
						<dt><i class="fa-solid fa-book" title={m.framework()}></i></dt>
						<dd class="truncate">
							{audit.framework}{#if !audit.exact}<span
									class="ml-1.5 text-xs"
									title={m.prereadByNumberHint()}>{m.prereadByNumber()}</span
								>{/if}{#if !audit.applies}<span
									class="ml-1.5 text-xs"
									title={m.prereadPartialHint()}>{m.prereadPartial()}</span
								>{/if}
						</dd>
						<dt><i class="fa-solid fa-sitemap" title={m.domain()}></i></dt>
						<dd class="truncate">{audit.folder?.str ?? '—'}</dd>
						<dt><i class="fa-solid fa-cubes" title={m.perimeter()}></i></dt>
						<dd class="truncate">
							{audit.perimeter?.str?.split('/').pop() ?? m.prereadNoPerimeter()}
						</dd>
					</dl>
					<span class="mt-auto text-sm text-primary-600-400 font-medium">
						{m.prereadOpen()}<i class="fa-solid fa-arrow-right ml-1.5"></i>
					</span>
				</a>
			{:else}
				<p class="text-sm text-surface-600-400">{m.prereadNoAuditMatches({ query })}</p>
			{/each}
		</div>
	{/if}
</div>
