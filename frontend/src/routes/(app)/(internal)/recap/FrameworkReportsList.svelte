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

<div class="space-y-3">
	<p class="text-sm text-surface-600-400">{m.frameworkReportsDescription()}</p>
	<label class="sr-only" for="framework-reports-search">{m.search()}</label>
	<input
		id="framework-reports-search"
		type="search"
		class="input max-w-sm"
		placeholder={m.search()}
		bind:value={search}
	/>
	{#if shown.length === 0}
		<p class="text-sm text-surface-600-400 italic">{m.noUsedFrameworks()}</p>
	{:else}
		<ul class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
			{#each shown as fw (fw.id)}
				<li>
					<a
						href="/frameworks/{fw.id}/report"
						class="flex items-center justify-between gap-3 rounded-xl border border-surface-200-800 p-3 hover:bg-surface-100-900"
					>
						<span class="font-medium">{fw.name}</span>
						<span class="badge preset-tonal-primary shrink-0">
							{m.auditsCount({ count: fw.compliance_assessments_count })}
						</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</div>
