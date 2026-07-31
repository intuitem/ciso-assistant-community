<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="p-4 space-y-4">
	<h1 class="h3">{m.threatCatalogs()}</h1>
	<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
		{#each data.catalogs as catalog (catalog.id)}
			<a
				href="/threat-catalogs/{catalog.id}"
				class="card p-4 preset-tonal-surface hover:preset-tonal-primary space-y-1"
			>
				<p class="font-semibold">{catalog.name}</p>
				<p class="text-xs text-surface-600-400">{catalog.ref_id}</p>
				{#if catalog.description}
					<p class="text-sm line-clamp-3">{catalog.description}</p>
				{/if}
			</a>
		{:else}
			<p class="text-surface-600-400">{m.noResults()}</p>
		{/each}
	</div>
</div>
