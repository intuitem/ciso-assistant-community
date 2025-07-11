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
		links: [
			{ source: 'blk-00', target: 'blk-02' },
			{ source: 'blk-01', target: 'blk-02' },
			{ source: 'blk-023', target: 'blk-11' },
			{ source: 'blk-11', target: 'blk-12' },
			{ source: 'blk-12', target: 'blk-13' },
			{ source: 'blk-13', target: 'blk-14' },
			{ source: 'blk-02', target: 'blk-023' },
			{ source: 'blk-022', target: 'blk-023' }
		]
	};

	const panelNodes = data.data.panelNodes;
</script>

{JSON.stringify(data.data, null, 2)}
<GraphComponent data={data2} {panelNodes} />
