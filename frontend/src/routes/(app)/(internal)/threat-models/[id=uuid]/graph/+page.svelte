<script lang="ts">
	import { SvelteFlowProvider } from '@xyflow/svelte';
	import { m } from '$paraglide/messages';
	import ThreatModelGraph from './ThreatModelGraph.svelte';
	import ViewSwitch from '../ViewSwitch.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const threatModel = $derived(data.threatModel);
	const graph = $derived(data.graph);
</script>

<div class="flex flex-col h-[calc(100vh-4rem)]">
	<div class="flex items-center justify-between gap-3 px-4 py-3 border-b border-surface-200-800">
		<div>
			<h1 class="h4">{threatModel.name}</h1>
			<p class="text-xs text-surface-600-400">{data.matrix.catalog.name}</p>
		</div>
		<div class="flex items-center gap-3">
			<ViewSwitch threatModelId={threatModel.id} active="graph" />
			<a class="btn preset-tonal-surface text-sm" href="/threat-models/{threatModel.id}">
				{m.details()}
			</a>
		</div>
	</div>

	<div class="flex-1 min-h-0">
		{#if graph.tactics.length}
			<SvelteFlowProvider>
				<ThreatModelGraph
					threatModelId={threatModel.id}
					tactics={graph.tactics}
					graphNodes={graph.nodes}
					graphEdges={graph.edges}
					graphColumns={graph.graph_columns}
					paletteTechniques={data.matrix.cells}
				/>
			</SvelteFlowProvider>
		{:else}
			<p class="p-4 text-surface-600-400">{m.noTTPCatalogMatrix()}</p>
		{/if}
	</div>
</div>
