<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape, GraphLinkArrowStyle } from '@unovis/ts';

	type NodeDatum = {
		id: string;
		label: string;
		group?: string;
		subGroup?: string;
		icon?: string;
		size?: number;
		shape?: GraphNodeShape;
	};

	type LinkDatum = {
		source: string;
		target: string;
	};

	type PanelConfig = {
		label: string;
		nodes: string[];
		padding?: { top: number; right: number; bottom: number; left: number };
		sideIconSymbol?: string;
		sideIconShape?: string;
		sideIconSymbolColor?: string;
		sideIconFontSize?: number;
		dashedOutline?: boolean;
		borderColor?: string;
	};

	type GraphData = {
		nodes: NodeDatum[];
		links: LinkDatum[];
	};

	// Props
	let {
		data,
		panelNodes = {
			reconnaissance: [],
			initialAccess: [],
			discovery: [],
			exploitation: []
		},
		height = '80vh',
		maxLineLength = 30,
		disableZoom = false,
		layoutType = GraphLayoutType.Parallel,
		layoutParallelGroupSpacing = 200
	}: {
		data: GraphData;
		panelNodes?: {
			reconnaissance: string[];
			initialAccess: string[];
			discovery: string[];
			exploitation: string[];
		};
		height?: string;
		maxLineLength?: number;
		disableZoom?: boolean;
		layoutType?: GraphLayoutType;
		layoutParallelGroupSpacing?: number;
	} = $props();

	// Build panels with configurable node assignments
	const panels = $derived([
		{
			label: 'Connaître',
			nodes: panelNodes.reconnaissance,
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
			nodes: panelNodes.initialAccess,
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
			nodes: panelNodes.discovery,
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
			nodes: panelNodes.exploitation,
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			sideIconSymbol: '&#xe4e9;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'red',
			sideIconFontSize: 30,
			borderColor: 'red',
			dashedOutline: true
		}
	]);

	// Configuration constants
	const DEFAULT_NODE_SHAPE = GraphNodeShape.Square;
	const DEFAULT_NODE_SIZE = 60;

	function wrapText(text: string, maxLength: number = maxLineLength): string[] {
		if (!text) return [];

		const paragraphs = text.split('\n');
		const wrappedLines: string[] = [];

		paragraphs.forEach((paragraph) => {
			if (paragraph.length <= maxLength) {
				wrappedLines.push(paragraph);
				return;
			}

			const words = paragraph.split(' ');
			let currentLine = '';

			words.forEach((word) => {
				if (currentLine.length + word.length + 1 > maxLength) {
					if (currentLine.trim()) {
						wrappedLines.push(currentLine.trim());
					}
					currentLine = word;
				} else {
					currentLine += (currentLine ? ' ' : '') + word;
				}
			});

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

	// Process the data with text wrapping
	const processedData = $derived({
		...data,
		nodes: processNodesWithWrapping(data.nodes)
	});

	// Graph configuration
	const nodeShape = (node: NodeDatum) => node.shape ?? DEFAULT_NODE_SHAPE;
	const nodeSize = (node: NodeDatum) => node.size ?? DEFAULT_NODE_SIZE;
	const nodeStrokeWidth = 2;
	const nodeStroke = '#4D179A';
	const nodeFill = '#FFFFFF';
	const linkStroke = '#8FA1B9';
	const linkArrow = GraphLinkArrowStyle.Single;
	const linkFlow = false;
	const linkArrowColor = '#4D179A';
	const linkArrowSize = 8;

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
					const currentNodeSize = node.size ?? DEFAULT_NODE_SIZE;
					const startY = currentNodeSize / 2 + 25 - totalHeight / 2 + lineHeight;

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
	<VisSingleContainer data={processedData} {height}>
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
			{disableZoom}
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
