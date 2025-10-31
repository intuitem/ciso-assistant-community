<script lang="ts">
	import type { PageData } from './$types';
	import AssetDependencyGraph from '$lib/components/Assets/AssetDependencyGraph.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-white p-4 shadow-sm rounded-lg space-y-4">
	<div class="flex justify-between items-center">
		<div class="flex-1">
			<h1 class="text-2xl font-bold">
				<i class="fa-solid fa-sitemap mr-2"></i>
				{m.assetDependencies()}
			</h1>
			<p class="text-sm text-gray-500 mt-1">{m.assetDependenciesDescription()}</p>
		</div>

		<!-- Legend -->
		<div class="flex items-center gap-6 text-sm">
			<div class="flex items-center gap-2">
				<div
					class="w-7 h-7 rounded-full flex items-center justify-center font-bold text-base"
					style="background-color: #47e845; color: white;"
				>
					✓
				</div>
				<span class="text-gray-700">{m.objectivesMet()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div
					class="w-7 h-7 rounded-full flex items-center justify-center font-bold text-base"
					style="background-color: #ffc226; color: white;"
				>
					⚠
				</div>
				<span class="text-gray-700">{m.objectivesNotMet()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div
					class="w-7 h-7 rounded-full flex items-center justify-center"
					style="background-color: #dddddd;"
				></div>
				<span class="text-gray-700">{m.noData()}</span>
			</div>
		</div>
	</div>

	{#if data.graphData.nodes.length === 0}
		<div class="card p-8 text-center">
			<i class="fa-solid fa-circle-info text-4xl text-gray-400 mb-4"></i>
			<p class="text-gray-600">{m.noDependenciesFound()}</p>
		</div>
	{:else}
		<AssetDependencyGraph data={data.graphData} />
	{/if}
</div>
