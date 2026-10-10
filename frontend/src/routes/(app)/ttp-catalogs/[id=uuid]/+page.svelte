<script lang="ts">
	import TTPMatrix from '$lib/components/TTPMatrix/TTPMatrix.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const matrix = $derived(data.matrix);
</script>

<div class="p-4 space-y-4">
	<div class="space-y-1">
		<h1 class="h3">{matrix.catalog.name}</h1>
		{#if matrix.catalog.description}
			<p class="text-sm text-surface-600-400 whitespace-pre-line">
				{matrix.catalog.description}
			</p>
		{/if}
	</div>

	{#if matrix.columns.length}
		<TTPMatrix
			columns={matrix.columns}
			cells={matrix.cells}
			facets={matrix.facets}
			href={(cell) => `/techniques/${cell.id}`}
		/>
	{:else}
		<p class="text-surface-600-400">{m.noTTPCatalogMatrix()}</p>
	{/if}
</div>
