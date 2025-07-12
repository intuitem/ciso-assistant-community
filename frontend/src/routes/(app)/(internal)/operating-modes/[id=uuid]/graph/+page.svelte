<script lang="ts">
	import GraphComponent from './OperatingModeGraph.svelte';
	import type { PageData } from './$types';
	interface Props {
		data: PageData;
	}
	import { m } from '$paraglide/messages';
	let { data }: Props = $props();
	const data2 = {
		nodes: data.data.nodes,
		links: data.data.links
	};
	const panelNodes = data.data.panelNodes;
	const linkFlow = data.animated; //?animated=true
</script>

<div class="flex justify-between items-center mb-4">
	<a
		class="text-primary-800 hover:text-primary-500 cursor-pointer"
		href="/operating-modes/{data.data.mo_id}/"
	>
		<i class="fa-solid fa-arrow-left mr-2"></i>{m.returnToMo()}
	</a>

	{#if data.animated}
		<a
			href="/operating-modes/{data.data.mo_id}/graph"
			data-sveltekit-reload
			class="text-primary-800 hover:text-primary-500 cursor-pointer"
		>
			{m.graphStop()}
		</a>
	{:else}
		<a
			href="/operating-modes/{data.data.mo_id}/graph?animated=true"
			data-sveltekit-reload
			class="text-primary-800 hover:text-primary-500 cursor-pointer"
		>
			{m.graphAnimate()}
		</a>
	{/if}
</div>

<div
	class="rounded-xl w-full bg-linear-to-r from-slate-50 to-white shadow mb-4 p-2 text-xs text-slate-600 whitespace-pre-line mr-auto"
>
	<i class="fa-solid fa-circle-info"></i>
	{m.graphMoHelp()}
</div>
<GraphComponent data={data2} {panelNodes} {linkFlow} />
