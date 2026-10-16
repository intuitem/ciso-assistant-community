<script lang="ts">
	import type { PageData } from './$types';
	import AssetDependencyGraph from '$lib/components/Assets/AssetDependencyGraph.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-surface-50-950 p-4 shadow-sm rounded-lg space-y-4">
	<div class="flex justify-between items-center">
		<div class="flex-1">
			<h1 class="text-2xl font-bold">
				<i class="fa-solid fa-sitemap mr-2"></i>
				{m.assetDependencies()}
			</h1>
			<p class="text-sm text-surface-600-400 mt-1">{m.assetDependenciesDescription()}</p>
		</div>
	</div>

	{#if data.graphData.nodes.length === 0}
		<div class="card p-8 text-center">
			<i class="fa-solid fa-circle-info text-4xl text-surface-400-600 mb-4"></i>
			<p class="text-surface-600-400">{m.noDependenciesFound()}</p>
		</div>
	{:else}
		<AssetDependencyGraph data={data.graphData} />
	{/if}
</div>
