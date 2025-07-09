<script lang="ts">
	import { label } from '$paraglide/messages';
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape } from '@unovis/ts';

	type NodeDatum = {
		id: string;
		label: string;
		group?: string;
		subGroup?: string;
	};

	const data = {
		nodes: [
			{ id: 'blk-00', label: 'space is cool, really really cool', group: 'grp0' },
			{
				id: 'blk-01',
				label:
					'Ea ut fugiat ullamco deserunt et consequat\n adipisicing veniam sunt nulla sit qui.',
				group: 'grp0'
			},
			{
				id: 'blk-02',
				label: 'Reconnaissance interne réseaux bureautique & IT site de Paris',
				group: 'grp1'
			},
			{ id: 'blk-11', group: 'grp2' },
			{ id: 'blk-12', group: 'grp3' }, // Keep them all in the same group
			{
				id: 'blk-13',
				label: 'Création et maintien d’un canal d’exfiltration via un poste Internet',
				group: 'grp3'
			},
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

	const panels = [
		{
			label: 'Connaître',
			nodes: ['blk-00', 'blk-01'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 }, // Increased vertical padding
			sideIconSymbol: '🔍',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'pink'
		},
		{
			label: 'Rentrer',
			nodes: ['blk-02'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 }, // Increased vertical padding
			sideIconSymbol: '🔐',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'violet'
		},
		{
			label: 'Trouver',
			nodes: ['blk-11'],
			padding: { top: 50, right: 50, bottom: 50, left: 50 }, // Increased vertical padding
			sideIconSymbol: '🎯',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'orange'
		},
		{
			label: 'Exploiter',
			nodes: ['blk-12', 'blk-13', 'blk-14'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 }, // Increased vertical padding
			sideIconSymbol: '💥',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			borderColor: 'red',
			dashedOutline: true
		}
	];
	const nodeShape = GraphNodeShape.Square;
	const nodeStrokeWidth = 2;
	const nodeStroke = '#4D179A';
	const nodeSize = 60;
	const nodeFill = '#FFFFFF';
	const linkStroke = '#8FA1B9';
	const layoutParallelGroupSpacing = 320;
	const nodeLabel = (n: NodeDatum) => n.label ?? n.id;
	const layoutType = GraphLayoutType.Parallel;
	const nodeLabelTrimLength = 40;
	const nodeLabelTrim = true;
</script>

<div class=" bg-slate-50">
	<VisSingleContainer {data} height={'80vh'}>
		<VisGraph
			{nodeShape}
			{nodeStroke}
			{nodeSize}
			{nodeFill}
			{nodeStrokeWidth}
			{nodeLabel}
			{nodeLabelTrim}
			{nodeLabelTrimLength}
			{layoutType}
			{panels}
			disableZoom
			{layoutParallelGroupSpacing}
			{linkStroke}
		/>
	</VisSingleContainer>
</div>
