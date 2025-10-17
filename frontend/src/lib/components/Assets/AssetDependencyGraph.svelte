<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape, GraphLinkArrowStyle } from '@unovis/ts';

	type NodeDatum = {
		id: string;
		label: string;
		folder: string;
		verdict?: boolean | null;
	};

	type LinkDatum = {
		source: string;
		target: string;
	};

	type GroupData = {
		id: string;
		name: string;
		nodes: string[];
	};

	type GraphData = {
		nodes: NodeDatum[];
		links: LinkDatum[];
		groups: GroupData[];
	};

	// Status map for verdict styling - using colors from Unovis example
	const StatusMap: Record<string, { color: string; text: string }> = {
		true: { color: '#47e845', text: '✓' }, // bright green with checkmark (objectives met)
		false: { color: '#ffc226', text: '⚠' }, // yellow with warning (objectives not met)
		null: { color: '#dddddd', text: '' } // light gray, no icon
	};

	// Props
	let {
		data,
		height = '70vh',
		maxLineLength = 20,
		disableZoom = false
	}: {
		data: GraphData;
		height?: string;
		maxLineLength?: number;
		disableZoom?: boolean;
	} = $props();

	// Build panels from groups (folders)
	const panels = $derived(
		data.groups.map((group) => ({
			label: group.name,
			nodes: group.nodes,
			padding: { top: 50, right: 60, bottom: 50, left: 60 },
			dashedOutline: true,
			borderColor: '#4D179A'
		}))
	);

	// Configuration constants
	const DEFAULT_NODE_SHAPE = GraphNodeShape.Hexagon;
	const DEFAULT_NODE_SIZE = 55;

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
			label: node.label ? wrapText(node.label, maxLineLength).join('\n') : node.label
		}));
	}

	// Process the data with text wrapping
	const processedData = $derived({
		...data,
		nodes: processNodesWithWrapping(data.nodes)
	});

	// Layout node group function to organize nodes by folder
	const layoutNodeGroup = (node: NodeDatum) => {
		return node.folder;
	};

	// Graph configuration
	const nodeShape = () => DEFAULT_NODE_SHAPE;
	const nodeSize = () => DEFAULT_NODE_SIZE;
	const nodeStrokeWidth = 3;

	// Color nodes based on verdict
	const nodeStroke = (node: NodeDatum) => {
		const status = String(node.verdict ?? 'null');
		return StatusMap[status]?.color || StatusMap['null'].color;
	};

	const nodeFill = () => '#ffffff'; // white fill for all nodes

	// Add status badge to nodes
	const nodeSideLabels = (node: NodeDatum) => {
		if (node.verdict === null || node.verdict === undefined) {
			return []; // No badge for nodes without verdict
		}

		const status = String(node.verdict);
		const statusConfig = StatusMap[status];

		if (!statusConfig) {
			return [];
		}

		return [
			{
				radius: 16,
				fontSize: 12,
				text: statusConfig.text
			}
		];
	};

	const linkStroke = '#8FA1B9';
	const linkArrow = GraphLinkArrowStyle.Single;
	const linkArrowColor = '#4D179A';
	const linkArrowSize = 8;
	const linkFlow = true;
	const linkBandWidth = 8;
	const layoutType = GraphLayoutType.Parallel;
	const layoutParallelGroupSpacing = 200;
	const layoutParallelNodesPerColumn = 6;

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

					lines.forEach((line, i) => {
						targetGroup
							.append('text')
							.attr('class', 'custom-multiline-label')
							.attr('text-anchor', 'middle')
							.attr('x', 0)
							.attr('y', i * lineHeight - (lines.length * lineHeight) / 2 + lineHeight / 2)
							.attr('font-size', '11px')
							.attr('font-weight', '500')
							.attr('fill', '#0F1E57')
							.style('font-family', 'var(--vis-font-family)')
							.text(line.trim());
					});
				}
			}
		});
	};

	const nodeLabel = () => ''; // Disable default labels to avoid overlap
</script>

<div class="chart bg-white rounded-lg shadow-sm">
	<VisSingleContainer data={processedData} {height}>
		<VisGraph
			{nodeShape}
			{nodeStroke}
			{nodeSize}
			{nodeFill}
			{nodeStrokeWidth}
			{nodeLabel}
			{nodeSideLabels}
			{onRenderComplete}
			{layoutType}
			{layoutNodeGroup}
			{panels}
			{disableZoom}
			{layoutParallelGroupSpacing}
			{layoutParallelNodesPerColumn}
			{linkStroke}
			{linkArrow}
			{linkArrowSize}
			{linkFlow}
			{linkBandWidth}
			{linkArrowColor}
		/>
	</VisSingleContainer>
</div>

<style>
	.chart {
		--vis-graph-link-stroke-opacity: 0.8;
		--vis-graph-link-band-opacity: 0.25;
		--vis-graph-panel-label-font-weight: 800;
		--vis-graph-link-stroke-color: #8fa1b9;
	}

	:global(.custom-multiline-label) {
		font-family: var(--vis-font-family);
		pointer-events: none;
	}
</style>
