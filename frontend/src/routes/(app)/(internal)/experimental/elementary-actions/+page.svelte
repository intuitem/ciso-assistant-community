<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape } from '@unovis/ts';

	export type NodeDatum = {
		id: string;
		group?: string;
		subGroup?: string;
	};

	export const data = {
		nodes: [
			{ id: 'blk-00', group: 'grp0', icon: '&#xf0c2;' },
			{ id: 'blk-01', group: 'grp0', icon: '&#xf233;' },
			{ id: 'blk-02', group: 'grp1', icon: '&#xf1b3;' },
			{ id: 'blk-11', group: 'grp2' },
			{ id: 'blk-12', group: 'grp3' }, // Keep them all in the same group
			{ id: 'blk-13', group: 'grp3' },
			{ id: 'blk-14', group: 'grp3', icon: '💎' }
		],
		links: [
			{ source: 'blk-00', target: 'blk-02' },
			{ source: 'blk-01', target: 'blk-02' },
			{ source: 'blk-02', target: 'blk-11' },
			{ source: 'blk-11', target: 'blk-12' },
			{ source: 'blk-12', target: 'blk-13' },
			{ source: 'blk-13', target: 'blk-14' }
		]
	};

	export const panels = [
		{
			label: 'connaitre',
			nodes: ['blk-00', 'blk-01'],
			padding: { top: 50, right: 50, bottom: 50, left: 50 }, // Increased vertical padding
			sideIconSymbol: '📋',
			sideIconShape: 'circle',
			sideIconShapeSize: 60,
			color: '#E3116C',
			borderColor: 'pink'
		},
		{
			label: 'rentrer',
			nodes: ['blk-02'],
			padding: { top: 50, right: 50, bottom: 50, left: 50 }, // Increased vertical padding
			sideIconSymbol: '🔐',
			sideIconShape: 'circle',
			sideIconShapeSize: 60,
			borderColor: 'violet'
		},
		{
			label: 'trouver',
			nodes: ['blk-11'],
			padding: { top: 50, right: 50, bottom: 50, left: 50 }, // Increased vertical padding
			sideIconSymbol: '🎯',
			sideIconShape: 'circle',
			sideIconShapeSize: 60,
			borderColor: 'orange'
		},
		{
			label: 'exploiter',
			nodes: ['blk-12', 'blk-13', 'blk-14'],
			padding: { top: 50, right: 50, bottom: 50, left: 50 }, // Increased vertical padding
			sideIconSymbol: '💥',
			sideIconShape: 'circle',
			sideIconShapeSize: 60,
			borderColor: 'red'
		}
	];
	const nodeShape = GraphNodeShape.Square;
	const nodeStrokeWidth = 2;
	const layoutParallelGroupSpacing = 320;
	const nodeLabel = (n: NodeDatum) => n.id;
	const layoutType = GraphLayoutType.Parallel;
</script>

<VisSingleContainer {data} height={'80vh'}>
	<VisGraph
		{nodeShape}
		{nodeStrokeWidth}
		{nodeLabel}
		{layoutType}
		{panels}
		disableZoom
		{layoutParallelGroupSpacing}
	/>
</VisSingleContainer>
