<script lang="ts">
	import { m } from '#paraglide/messages.js';

	type UsedFramework = { id: string; name: string; compliance_assessments_count: number };
	let { frameworks }: { frameworks: UsedFramework[] } = $props();

	let search = $state('');
	let shown = $derived(
		[...frameworks]
			.filter((fw) => fw.name.toLowerCase().includes(search.trim().toLowerCase()))
			.sort((a, b) => a.name.localeCompare(b.name))
	);
</script>

<div class="space-y-4">
	<div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_20rem] md:items-center">
		<p class="text-sm text-surface-600-400">{m.frameworkReportsDescription()}</p>
		<label class="sr-only" for="framework-reports-search">{m.search()}</label>
		<input
			id="framework-reports-search"
			type="search"
			class="input w-full"
			placeholder={m.search()}
			bind:value={search}
		/>
	</div>
	{#if shown.length === 0}
		<p class="text-sm text-surface-600-400 italic">{m.noUsedFrameworks()}</p>
	{:else}
		<ul class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
			{#each shown as fw (fw.id)}
				<li>
					<a
						href="/frameworks/{fw.id}/report"
						class="group grid h-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-xl border border-surface-200-800 bg-surface-50-950 p-4 transition hover:border-primary-400 hover:shadow-md"
					>
						<span
							class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300"
							aria-hidden="true"><i class="fa-solid fa-chart-pie"></i></span
						>
						<span class="min-w-0">
							<span class="block font-medium line-clamp-2" title={fw.name}>{fw.name}</span>
							<span class="text-xs text-surface-600-400">
								{m.auditsCount({ count: fw.compliance_assessments_count })}
							</span>
						</span>
						<i
							class="fa-solid fa-arrow-right text-surface-400 transition group-hover:translate-x-0.5 group-hover:text-primary-500"
							aria-hidden="true"
						></i>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</div>
