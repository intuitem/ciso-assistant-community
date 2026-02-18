<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set(data.data.meta.display_name);

	const {
		source_framework,
		target_framework,
		source_coverage,
		target_coverage,
		source_total,
		source_linked,
		target_total,
		target_linked
	} = data.data.meta;
</script>

<div class="bg-surface-50-950 shadow-sm flex flex-col overflow-x-auto">
	<div class="px-4 py-2 border-b border-surface-200-800 flex flex-col gap-1 text-sm">
		<div>
			<span class="text-surface-600-400">{source_framework} → {target_framework}:</span>
			<span class="font-semibold">{target_coverage ?? 0}%</span>
			<span class="text-surface-400-600">({target_linked}/{target_total})</span>
		</div>
		<div>
			<span class="text-surface-600-400">{target_framework} → {source_framework}:</span>
			<span class="font-semibold">{source_coverage ?? 0}%</span>
			<span class="text-surface-400-600">({source_linked}/{source_total})</span>
		</div>
	</div>
	<div class="w-full h-screen">
		<GraphExplorer title="Mapping Explorer" data={data.data} />
	</div>
</div>
