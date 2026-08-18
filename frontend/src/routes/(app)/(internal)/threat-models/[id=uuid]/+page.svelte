<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { SvelteFlowProvider } from '@xyflow/svelte';
	import ThreatModelGraph from './graph/ThreatModelGraph.svelte';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const graph = $derived(data.graph);
	const hasNodes = $derived((graph?.nodes?.length ?? 0) > 0);
</script>

<DetailView {data} />

<div class="card m-4 p-4 bg-surface-50-950 shadow-lg">
	<div class="flex items-center justify-between gap-2 mb-3">
		<div class="flex items-center gap-2">
			<i class="fa-solid fa-diagram-project text-xs text-indigo-400"></i>
			<span class="text-xs font-semibold uppercase tracking-wider text-surface-400-600">
				{m.graph()}
			</span>
		</div>
		<div class="flex items-center gap-2">
			<Anchor
				breadcrumbAction="push"
				href={`${page.url.pathname}/select`}
				class="btn btn-sm preset-tonal-secondary"
			>
				<i class="fa-solid fa-table-cells mr-1"></i>{m.selectTechniques()}
			</Anchor>
			<Anchor
				breadcrumbAction="push"
				href={`${page.url.pathname}/graph`}
				class="btn btn-sm preset-filled-secondary-500"
			>
				<i class="fa-solid fa-pen mr-1"></i>{m.editGraph()}
			</Anchor>
		</div>
	</div>

	{#if hasNodes}
		<div class="h-[28rem]">
			<SvelteFlowProvider>
				<ThreatModelGraph
					threatModelId={data.data.id}
					tactics={graph.tactics}
					graphNodes={graph.nodes}
					graphEdges={graph.edges}
					graphColumns={graph.graph_columns}
					paletteTechniques={[]}
					readonly
				/>
			</SvelteFlowProvider>
		</div>
	{:else}
		<div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
			<i class="fa-solid fa-diagram-project text-3xl text-surface-300-700"></i>
			<p class="text-sm text-surface-600-400">{m.threatModelEmptyGraph()}</p>
			<Anchor
				breadcrumbAction="push"
				href={`${page.url.pathname}/select`}
				class="btn btn-sm preset-filled-primary-500"
			>
				{m.selectTechniques()}
			</Anchor>
		</div>
	{/if}
</div>
