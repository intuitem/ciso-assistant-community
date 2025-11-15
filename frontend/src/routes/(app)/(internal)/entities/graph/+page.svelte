<script lang="ts">
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-white shadow-sm flex flex-col overflow-x-auto">
	<div class="flex justify-between items-center p-4 border-b border-gray-200">
		<h1 class="text-2xl font-semibold text-gray-900">
			<i class="fa-solid fa-diagram-project mr-2"></i>
			{m.entitiesGraph()}
		</h1>
		<a href="/entities" class="text-primary-800 hover:text-primary-500 cursor-pointer">
			<i class="fa-solid fa-arrow-left mr-2"></i>
			{m.backToTable()}
		</a>
	</div>
	<div class="w-full h-screen">
		<GraphExplorer
			title="Entities Graph"
			data={data.data}
			edgeLength={120}
			maxLegendItems={10}
			showNodeLabels={false}
		/>
	</div>
</div>
