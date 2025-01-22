<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import type { PageData } from './$types';
	export let data: PageData;
	const mapping_sets = data.data.results;
</script>

<div>
	<ul class="list-disc p-4 m-2">
		{#each mapping_sets as mset}
			<li class="">
				<Anchor href={`/experimental/mapping/${mset.id}`} class="text-md hover:text-purple-700"
					>{mset.name}</Anchor
				>
			</li>
		{/each}
	</ul>
</div>
