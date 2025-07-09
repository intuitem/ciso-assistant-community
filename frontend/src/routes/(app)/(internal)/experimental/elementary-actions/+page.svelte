<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape } from '@unovis/ts';

	type NodeDatum = {
		id: string;
		label: string;
		group?: string;
		subGroup?: string;
		icon?: string;
	};

	// Configuration constant for maximum line length
	const MAX_LINE_LENGTH = 30;

	/**
	 * Helper function to wrap text based on maximum line length
	 * @param text - The text to wrap
	 * @param maxLength - Maximum characters per line
	 * @returns Array of wrapped lines
	 */
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

	/**
	 * Process node data to apply text wrapping
	 * @param nodes - Array of node data
	 * @returns Processed nodes with wrapped text
	 */
	function processNodesWithWrapping(nodes: NodeDatum[]): NodeDatum[] {
		return nodes.map((node) => ({
			...node,
			label: node.label ? wrapText(node.label).join('\n') : node.label
		}));
	}

	const rawData = {
		nodes: [
			{ id: 'blk-00', label: 'space is cool, really really cool', group: 'grp0' },
			{
				id: 'blk-01',
				label: 'Ea ut fugiat ullamco deserunt et consequat adipisicing veniam sunt nulla sit qui.',
				group: 'grp0'
			},
			{
				id: 'blk-02',
				label: 'Reconnaissance interne réseaux bureautique & IT site de Paris',
				group: 'grp1'
			},
			{
				id: 'blk-11',
				label:
					'Irure aliqua cillum consequat consectetur tempor fugiat exercita<D-b>tion ad ex mollit culpa.',
				group: 'grp2'
			},
			{
				id: 'blk-12',
				label:
					'Irure aliqua cillum consequat consectetur tempor fugiat exercitation ad ex mollit culpa.',
				group: 'grp3'
			},
			{
				id: 'blk-13',
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
			nodes: ['blk-00', 'blk-01'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			sideIconSymbol: '🔍',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'pink'
		},
		{
			label: 'Rentrer',
			nodes: ['blk-02'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			sideIconSymbol: '🔐',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'violet'
		},
		{
			label: 'Trouver',
			nodes: ['blk-11'],
			padding: { top: 50, right: 50, bottom: 50, left: 50 },
			sideIconSymbol: '🎯',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'orange'
		},
		{
			label: 'Exploiter',
			nodes: ['blk-12', 'blk-13', 'blk-14'],
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			sideIconSymbol: '💥',
			sideIconShape: 'circle',
			sideIconFontSize: 30,
			borderColor: 'red',
			dashedOutline: true
		}
	];

	// Graph configuration
	const nodeShape = GraphNodeShape.Square;
	const nodeStrokeWidth = 2;
	const nodeStroke = '#4D179A';
	const nodeSize = 60;
	const nodeFill = '#FFFFFF';
	const linkStroke = '#8FA1B9';
	const layoutParallelGroupSpacing = 200;
	const layoutType = GraphLayoutType.Parallel;

	// Custom function to add multiline labels after default rendering
	const onRenderComplete = (g, nodes, links, config) => {
		// Remove existing custom labels first
		g.selectAll('.custom-multiline-label').remove();

		// Add multiline labels for each node using the data
		nodes.forEach((node) => {
			if (node.label && node.label.includes('\n')) {
				// Find the node group by iterating through DOM nodes
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
					const lines = node.label.split('\n');
					const lineHeight = 12;
					const startY = config.nodeSize / 2 + 20;

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
							.text(line);
					});
				}
			}
		});
	};

	const nodeLabel = (n: NodeDatum) => ''; // Disable default labels to avoid overlap
	const nodeIcon = (n: NodeDatum) => n.icon || ''; // Enable icons
</script>

<div class=" bg-linear-to-br from-slate-100 to-white">
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
		/>
	</VisSingleContainer>
</div>
