<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape, GraphLinkArrowStyle } from '@unovis/ts';

	import { m } from '$paraglide/messages';
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
		linkFlow = false,
		layoutType = GraphLayoutType.Parallel,
		layoutParallelGroupSpacing = 250, // Increased from 200 for more space between columns
		layoutParallelNodesPerColumn = 5, // Reduced from 4 to spread nodes more
		layoutParallelSubGroupsPerRow = 3, // Control sub-groups per row
		zoomLevel = 1.0 // Default zoom level
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
		linkFlow?: boolean;
		layoutType?: GraphLayoutType;
		layoutParallelGroupSpacing?: number;
		layoutParallelNodesPerColumn?: number;
		layoutParallelSubGroupsPerRow?: number;
		zoomLevel?: number;
	} = $props();

	// Build panels with increased padding for more space
	const panels = $derived([
		{
			label: m.ebiosReconnaissance(),
			nodes: panelNodes.reconnaissance,
			padding: { top: 50, right: 80, bottom: 50, left: 80 }, // Increased horizontal padding
			sideIconSymbol: '&#xf002;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'pink',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'pink'
		},
		{
			label: m.ebiosInitialAccess(),
			nodes: panelNodes.initialAccess,
			padding: { top: 50, right: 80, bottom: 50, left: 80 }, // Increased horizontal padding
			sideIconSymbol: '&#xf504;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'violet',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'violet'
		},
		{
			label: m.ebiosDiscovery(),
			nodes: panelNodes.discovery,
			padding: { top: 50, right: 80, bottom: 50, left: 80 }, // Increased horizontal padding
			sideIconSymbol: '&#xf140;',
			sideIconShape: 'circle',
			sideIconSymbolColor: 'orange',
			sideIconFontSize: 30,
			dashedOutline: true,
			borderColor: 'orange'
		},
		{
			label: m.ebiosExploitation(),
			nodes: panelNodes.exploitation,
			padding: { top: 50, right: 80, bottom: 50, left: 80 }, // Increased horizontal padding
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
	const DEFAULT_NODE_SIZE = 70;

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
			label: node.label ? wrapText(node.label, 22).join('\n') : node.label
		}));
	}

	// Process the data with text wrapping
	const processedData = $derived({
		...data,
		nodes: processNodesWithWrapping(data.nodes)
	});

	// Layout node group function to organize nodes by panel assignment
	const layoutNodeGroup = (node: NodeDatum) => {
		if (panelNodes.reconnaissance.includes(node.id)) return 'reconnaissance';
		if (panelNodes.initialAccess.includes(node.id)) return 'initialAccess';
		if (panelNodes.discovery.includes(node.id)) return 'discovery';
		if (panelNodes.exploitation.includes(node.id)) return 'exploitation';
		return 'other'; // fallback for nodes not in any panel
	};

	// Sub-group function to organize nodes by their group property within each panel
	const layoutParallelNodeSubGroup = (node: NodeDatum) => {
		return node.group || 'default';
	};

	// Graph configuration
	const nodeShape = (node: NodeDatum) => node.shape ?? DEFAULT_NODE_SHAPE;
	const nodeSize = (node: NodeDatum) => node.size ?? DEFAULT_NODE_SIZE;
	const nodeStrokeWidth = 1.5;
	const nodeStroke = '#4D179A';
	const nodeFill = '#FFFFFF';
	const linkStroke = '#8FA1B9';
	const linkArrow = GraphLinkArrowStyle.Single;
	const linkArrowColor = '#4D179A';
	const linkArrowSize = 8;

	// Custom function to add labels after default rendering
	const onRenderComplete = (g, nodes, links, config) => {
		g.selectAll('.custom-multiline-label').remove();

		const nodeMap = new Map();
		g.selectAll('g').each(function () {
			const data = this.__data__;
			if (data?.id) {
				nodeMap.set(data.id, this);
			}
		});
		nodes.forEach((node) => {
			if (node.label) {
				const groupElement = nodeMap.get(node.id);
				const targetGroup = groupElement ? g.select(() => groupElement) : null;

				if (targetGroup) {
					const lines = node.label.split('\n').filter((line) => line.trim() !== '');

					if (lines.length === 0 && node.label.trim()) {
						lines.push(node.label.trim());
					}

					const lineHeight = 12;
					const totalHeight = lines.length * lineHeight;
					const currentNodeSize = node.size ?? DEFAULT_NODE_SIZE;
					const startY = 0;

					lines.forEach((line, i) => {
						targetGroup
							.append('text')
							.attr('class', 'custom-multiline-label')
							.attr('text-anchor', 'middle')
							.attr('x', 0)
							.attr('y', startY + i * lineHeight)
							.attr('font-size', '12px')
							.attr('font-weight', '400')
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
			{layoutNodeGroup}
			{layoutParallelNodeSubGroup}
			{panels}
			{disableZoom}
			{layoutParallelGroupSpacing}
			{layoutParallelNodesPerColumn}
			{layoutParallelSubGroupsPerRow}
			{linkStroke}
			{linkArrow}
			{linkFlow}
			{linkArrowSize}
			zoomScaleExtent={[zoomLevel, zoomLevel]}
		/>
	</VisSingleContainer>
</div>

<style>
	:global(.custom-multiline-label) {
		font-family: var(--vis-font-family);
		pointer-events: none;
	}
	:global(:root) {
		--vis-graph-panel-label-font-weight: 800;
		--vis-graph-link-stroke-color: #8fa1b9;
	}
</style>
