<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape, Graph } from '@unovis/ts';
	import type { PageData } from './$types';
	export let data: PageData;

	type NodeDatum = {
		id: string;
		label: string;
		color?: string;
		shape?: string;
		counter?: number;
	};

	type LinkDatum = {
		source: string;
		target: string;
		coverage: string;
		active?: boolean; // Added this property based on usage in linkFlow
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

	const forceLayoutSettings = {
		forceXStrength: 0.1,
		forceYStrength: 0.1,
		charge: -800
	};

	let containerHeight = '80vh';
	let selectedNodeId: string | undefined;

	function handleNodeClick(node: NodeDatum) {
		selectedNodeId = node.id;
		// this is ugly but the only trick I've found so far
		containerHeight = '80.1vh';
	}

	function handleBackgroundClick() {
		selectedNodeId = undefined;
		containerHeight = '80vh';
	}

	// Setup events for node and background clicks
	const events = {
		[Graph.selectors.node]: {
			click: handleNodeClick
		},
		[Graph.selectors.background]: {
			click: handleBackgroundClick
		}
	};
</script>

<div class="bg-white p-4 h-full w-full">
	<VisSingleContainer data={gdata} height={containerHeight}>
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
			{events}
			{selectedNodeId}
		/>
	</VisSingleContainer>
</div>

{#if selectedNodeId}
	<p>Selected Node: {selectedNodeId}</p>
{/if}
