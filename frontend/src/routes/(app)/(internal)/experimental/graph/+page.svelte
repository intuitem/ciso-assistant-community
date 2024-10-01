<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape } from '@unovis/ts';
	import type { PageData } from './$types';
	export let data: PageData;
	type NodeDatum = {
		id: string;
		color?: string;
		shape?: string;
		counter?: number;
	};

	type LinkDatum = {
		source: string;
		target: string;
		coverage: string;
	};

	type GraphData = {
		nodes: NodeDatum[];
		links: LinkDatum[];
	};

	const nodes: NodeDatum[] = data.data.nodes;

	const links: LinkDatum[] = data.data.links;

	const gdata: GraphData = { nodes, links };
	const linkLabel = (l: LinkDatum) => ({ text: l.coverage });
	const nodeLabel = (n: NodeDatum) => n.label;
	const nodeShape = (n: NodeDatum) => n.shape as GraphNodeShape;
	const nodeStroke = (n: NodeDatum) => n.color;
	const linkFlow = (l: LinkDatum) => l.active;
	const nodeDisabled = (n: NodeDatum, i: number) => n.counter < 1;
	const nodeSideLabels = (n: NodeDatum) => (n.counter ? [{ text: `${n.counter}` }] : []);
	const forceLayoutSettings: GraphForceLayoutSettings = {
		forceXStrength: 0.1,
		forceYStrength: 0.1,
		charge: -800
	};
</script>

<div class="bg-white p-4">
	<VisSingleContainer data={gdata} height={'60vh'}>
		<VisGraph
			layoutType={GraphLayoutType.Force}
			nodeSize={40}
			{forceLayoutSettings}
			{linkLabel}
			{nodeStroke}
			{nodeLabel}
			{nodeShape}
			{linkFlow}
			{nodeSideLabels}
			{nodeDisabled}
		/>
	</VisSingleContainer>
</div>
