<script lang="ts">
	import { GraphLayoutType, GraphNodeShape } from '@unovis/ts';
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

<a
	class="text-primary-800 hover:text-primary-500 cursor-pointer"
	href="/operating-modes/{data.data.mo_id}/"
>
	<i class="fa-solid fa-arrow-left mr-2"></i>{m.returnToMo()}</a
>
<GraphComponent data={data2} {panelNodes} {linkFlow} />
