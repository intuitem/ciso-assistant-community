<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape } from '@unovis/ts';
	export type NodeDatum = {
		id: string;
		label: string;
		shape: string;
		color: string;
	};

	export type LinkDatum = {
		id: string;
		source: string;
		target: string;
		active: boolean;
		color: string;
	};

	export type GraphData = {
		nodes: NodeDatum[];
		links: LinkDatum[];
	};

	export const links: LinkDatum[] = [
		{
			id: ':S:cartservice.app~:S:cart.app',
			source: 'S:cartservice.app',
			target: 'S:cart.app',
			active: true,
			color: '#35D068'
		}
	];

	export const nodes: NodeDatum[] = [
		{
			id: 'RO:123',
			label: 'Risk Origin',
			shape: 'hexagon',
			color: '#35D068'
		},
		{
			id: 'TO:123',
			label: 'Target Objective,\nlong text eventually telling a short story',
			shape: 'square',
			color: '#35D068'
		},
		{
			id: 'S:frontend.app',
			label: 'frontend.app',
			shape: 'hexagon',
			color: '#35D068'
		},
		{
			id: 'S:recommendationservice.app',
			label: 'recommendationservice.app',
			shape: 'hexagon',
			color: '#35D068'
		}
	];

	export const data: GraphData = { nodes, links };

	const layoutType = GraphLayoutType.Dagre;
	const nodeLabel = (n: NodeDatum) => n.label;
	const nodeShape = (n: NodeDatum) => n.shape as GraphNodeShape;
	const nodeStroke = (l: LinkDatum) => l.color;
	const linkFlow = (l: LinkDatum) => l.active;
	const linkStroke = (l: LinkDatum) => l.color;
</script>

<VisSingleContainer {data} height={'80vh'} class="card bg-white">
	<VisGraph {layoutType} {nodeLabel} {nodeShape} {nodeStroke} {linkFlow} {linkStroke} />
</VisSingleContainer>
