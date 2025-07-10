<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape, GraphLinkArrowStyle } from '@unovis/ts';

	type NodeDatum = {
		id: string;
		label: string;
		group?: string;
		subGroup?: string;
		icon?: string;
	};

	// Configuration constant for maximum line length
	const MAX_LINE_LENGTH = 30;

	function wrapText(text: string, maxLength: number = MAX_LINE_LENGTH): string[] {
		if (!text) return [];

		// Split by existing newlines first
		const paragraphs = text.split('\n');
		const wrappedLines: string[] = [];

		paragraphs.forEach((paragraph) => {
			if (paragraph.length <= maxLength) {
				wrappedLines.push(paragraph);
				return;
			}

			// Split long paragraphs into words
			const words = paragraph.split(' ');
			let currentLine = '';

			words.forEach((word) => {
				// If adding this word would exceed max length, start a new line
				if (currentLine.length + word.length + 1 > maxLength) {
					if (currentLine.trim()) {
						wrappedLines.push(currentLine.trim());
					}
					currentLine = word;
				} else {
					currentLine += (currentLine ? ' ' : '') + word;
				}
			});

			// Add the last line if it exists
			if (currentLine.trim()) {
				wrappedLines.push(currentLine.trim());
			}
		});

		return wrappedLines;
	}

	function processNodesWithWrapping(nodes: NodeDatum[]): NodeDatum[] {
		return nodes.map((node) => ({
			...node,
			label: node.label ? wrapText(node.label).join('\n') : node.label
		}));
	}

	const rawData = {
		nodes: [
			{ id: 'blk-00', label: 'space is cool, really really cool', group: 'grp0', icon: '&#xf0c2;' },
			{ id: 'blk-03', label: 'this is nice', group: 'grp0', icon: '&#xe4e5;' },
			{ id: 'blk-04', label: 'this is pretty', group: 'grp0', icon: '&#xf3cd;' },
			{
				id: 'blk-01',
				label: 'Ea ut fugiat ullamco deserunt et consequat adipisicing veniam sunt nulla sit qui.',
				group: 'grp0',
				icon: '&#xf233;'
			},
			{
				id: 'blk-02',
				label: 'Reconnaissance interne réseaux bureautique & IT site de Paris',
				group: 'grp1',
				icon: '&#xf1b3;'
			},
			{
				id: 'blk-022',
				label: 'Reconnaissance interne réseaux bureautique & IT site de Paris',
				group: 'grp1',
				icon: '&#xf6ff;'
			},
			{
				id: 'blk-023',
				group: 'grp1',
				icon: '|'
			},
			{ id: 'blk-11', label: 'short', group: 'grp2', icon: '&#xf1b2;' },
			{ id: 'blk-12', label: 'abc', group: 'grp3', icon: '&#xf15b;' },
			{
				id: 'blk-13',
				icon: '&#xf084;',
				label: "Création et maintien d'un canal d'exfiltration via un poste Internet",
				group: 'grp3'
			},
			{ id: 'blk-14', label: 'Vol et exploitation de données de R&D', group: 'grp3', icon: '💎' }
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

	// Process the data with text wrapping
	const data = {
		...rawData,
		nodes: processNodesWithWrapping(rawData.nodes)
	};

	const panels = [
		{
			label: 'Connaître',
			nodes: ['blk-00', 'blk-01', 'blk-03', 'blk-04'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			sideIconSymbol: '&#xf002;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'pink',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'pink'
		},
		{
			label: 'Rentrer',
			nodes: ['blk-02', 'blk-022', 'blk-023'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			sideIconSymbol: '&#xf504;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'violet',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'violet'
		},
		{
			label: 'Trouver',
			nodes: ['blk-11'],
			padding: { top: 50, right: 50, bottom: 50, left: 50 },
			sideIconSymbol: '&#xf140;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'orange',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'orange'
		},
		{
			label: 'Exploiter',
			nodes: ['blk-12', 'blk-13', 'blk-14'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			sideIconSymbol: '&#xe4e9;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'red',
			sideIconFontSize: 30,
			borderColor: 'red',
			dashedOutline: true
		}
	];

	// Graph configuration
	const nodeShape = GraphNodeShape.Square;
	const nodeStrokeWidth = 2;
	const nodeStroke = '#4D179A';
	const nodeSize = 60; // Increased size to accommodate multiline text
	const nodeFill = '#FFFFFF';
	const linkStroke = '#8FA1B9';
	const linkArrow = GraphLinkArrowStyle.Single; // Enable single arrow heads on links
	const linkFlow = false; // animation
	const linkArrowColor = '#4D179A'; // Make arrows more visible with darker color
	const linkArrowSize = 8; // Make arrows larger for better visibility
	const layoutParallelGroupSpacing = 200;
	const layoutType = GraphLayoutType.Parallel;

	// Custom function to add labels after default rendering
	const onRenderComplete = (g, nodes, links, config) => {
		g.selectAll('.custom-multiline-label').remove();

		nodes.forEach((node) => {
			if (node.label) {
				const allNodeGroups = g.selectAll('g').nodes();
				let targetGroup = null;

				for (let groupElement of allNodeGroups) {
					const groupData = groupElement.__data__;
					if (groupData && groupData.id === node.id) {
						targetGroup = g.select(() => groupElement);
						break;
					}
				}

				if (targetGroup) {
					const lines = node.label.split('\n').filter((line) => line.trim() !== '');

					if (lines.length === 0 && node.label.trim()) {
						lines.push(node.label.trim());
					}

					const lineHeight = 12;
					const totalHeight = lines.length * lineHeight;
					const startY = config.nodeSize / 2 + 25 - totalHeight / 2 + lineHeight;

					lines.forEach((line, i) => {
						targetGroup
							.append('text')
							.attr('class', 'custom-multiline-label')
							.attr('text-anchor', 'middle')
							.attr('x', 0)
							.attr('y', startY + i * lineHeight)
							.attr('font-size', '10px')
							.attr('fill', '#0F1E57')
							.style('font-family', 'var(--vis-font-family)')
							.text(line.trim());
					});
				}
			}
		});
	};

	const nodeLabel = (n: NodeDatum) => ''; // Disable default labels to avoid overlap
	const nodeIcon = (n: NodeDatum) => n.icon || ''; // Enable icons
</script>

<div class="bg-white">
	<VisSingleContainer {data} height={'80vh'}>
		<VisGraph
			{nodeShape}
			{nodeStroke}
			{nodeSize}
			{nodeFill}
			{nodeStrokeWidth}
			{nodeLabel}
			{nodeIcon}
			{onRenderComplete}
			{layoutType}
			{panels}
			disableZoom
			{layoutParallelGroupSpacing}
			{linkStroke}
			{linkArrow}
			{linkFlow}
			{linkArrowColor}
			{linkArrowSize}
		/>
	</VisSingleContainer>
</div>

<style>
	:global(.custom-multiline-label) {
		font-family: var(--vis-font-family);
		pointer-events: none;
	}
</style>
