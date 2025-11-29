<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape, GraphLinkArrowStyle } from '@unovis/ts';
	import { m } from '$paraglide/messages';

	type NodeDatum = {
		id: string;
		label: string;
		type: 'ro' | 'stakeholder' | 'asset' | 'feared_event';
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

	type AttackPath = {
		id: string;
		name: string;
		ref_id?: string;
		description?: string;
		stakeholders: Array<{
			id: string;
			str: string;
			category?: string;
			entity?: {
				id: string;
				name: string;
			};
		}>;
		risk_origin?: string;
		target_objective?: string;
		ro_to_couple?: {
			id: string;
			str: string;
		};
	};

	type FearedEvent = {
		id: string;
		name: string;
		ref_id?: string;
		assets: Array<{
			id: string;
			str: string;
			name?: string;
		}>;
	};

	// Props
	let {
		attackPaths,
		fearedEvents = [],
		height = '600px',
		maxLineLength = 20,
		disableZoom = false
	}: {
		attackPaths: AttackPath[];
		fearedEvents?: FearedEvent[];
		height?: string;
		maxLineLength?: number;
		disableZoom?: boolean;
	} = $props();

	// Build graph data from attack paths and feared events
	const graphData = $derived.by(() => {
		const nodes: NodeDatum[] = [];
		const links: LinkDatum[] = [];
		const nodeIds = new Set<string>();

		// Column 1: Add Risk Origin nodes
		attackPaths.forEach((path) => {
			if (path.risk_origin && !nodeIds.has(`ro-${path.risk_origin}`)) {
				nodes.push({
					id: `ro-${path.risk_origin}`,
					label: path.risk_origin,
					type: 'ro',
					shape: GraphNodeShape.Circle,
					size: 70
				});
				nodeIds.add(`ro-${path.risk_origin}`);
			}
		});

		// Column 2: Add Stakeholder (Ecosystem) nodes
		attackPaths.forEach((path) => {
			path.stakeholders?.forEach((stakeholder) => {
				const nodeId = `stakeholder-${stakeholder.id}`;
				if (!nodeIds.has(nodeId)) {
					// Include entity info in label if available
					const label = stakeholder.entity
						? `${stakeholder.str}\n(${stakeholder.entity.name})`
						: stakeholder.str;

					nodes.push({
						id: nodeId,
						label: label,
						type: 'stakeholder',
						shape: GraphNodeShape.Square,
						size: 60
					});
					nodeIds.add(nodeId);
				}

				// Link RO → Stakeholder
				if (path.risk_origin) {
					const linkId = `${path.risk_origin}-${stakeholder.id}`;
					if (!links.find((l) => `${l.source}-${l.target}` === linkId)) {
						links.push({
							source: `ro-${path.risk_origin}`,
							target: nodeId
						});
					}
				}
			});
		});

		// Column 3: Add Asset nodes and Feared Event nodes
		fearedEvents.forEach((fearedEvent) => {
			// Add feared event node
			const feNodeId = `fe-${fearedEvent.id}`;
			if (!nodeIds.has(feNodeId)) {
				nodes.push({
					id: feNodeId,
					label: fearedEvent.ref_id
						? `${fearedEvent.ref_id}\n${fearedEvent.name}`
						: fearedEvent.name,
					type: 'feared_event',
					shape: GraphNodeShape.Hexagon,
					size: 65
				});
				nodeIds.add(feNodeId);
			}

			// Add asset nodes
			fearedEvent.assets?.forEach((asset) => {
				const assetNodeId = `asset-${asset.id}`;
				if (!nodeIds.has(assetNodeId)) {
					nodes.push({
						id: assetNodeId,
						label: asset.str || asset.name || '',
						type: 'asset',
						shape: GraphNodeShape.Triangle,
						size: 55
					});
					nodeIds.add(assetNodeId);
				}

				// Link Feared Event → Asset
				links.push({
					source: feNodeId,
					target: assetNodeId
				});
			});
		});

		// Link Stakeholders → Feared Events
		// All stakeholders can potentially lead to all feared events in the strategic scenario
		attackPaths.forEach((path) => {
			path.stakeholders?.forEach((stakeholder) => {
				fearedEvents.forEach((fearedEvent) => {
					const linkId = `${stakeholder.id}-${fearedEvent.id}`;
					if (!links.find((l) => `${l.source}-${l.target}` === linkId)) {
						links.push({
							source: `stakeholder-${stakeholder.id}`,
							target: `fe-${fearedEvent.id}`
						});
					}
				});
			});
		});

		return { nodes, links };
	});

	// Build panels for layout with 3 columns
	const panels = $derived([
		{
			label: m.riskOrigins(),
			nodes: graphData.nodes.filter((n) => n.type === 'ro').map((n) => n.id),
			padding: { top: 60, right: 80, bottom: 60, left: 80 },
			dashedOutline: true,
			borderColor: '#dc2626',
			sideIconSymbol: '&#xf071;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#dc2626'
		},
		{
			label: m.studyTheEcosystem(),
			nodes: graphData.nodes.filter((n) => n.type === 'stakeholder').map((n) => n.id),
			padding: { top: 60, right: 80, bottom: 60, left: 80 },
			dashedOutline: true,
			borderColor: '#f59e0b',
			sideIconSymbol: '&#xf0c0;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#f59e0b'
		},
		{
			label: `${m.assets()} & ${m.fearedEvents()}`,
			nodes: graphData.nodes
				.filter((n) => n.type === 'asset' || n.type === 'feared_event')
				.map((n) => n.id),
			padding: { top: 60, right: 80, bottom: 60, left: 80 },
			dashedOutline: true,
			borderColor: '#16a34a',
			sideIconSymbol: '&#xf530;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#16a34a'
		}
	]);

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
		...graphData,
		nodes: processNodesWithWrapping(graphData.nodes)
	});

	// Layout node group function to organize into 3 columns
	const layoutNodeGroup = (node: NodeDatum) => {
		return node.type;
	};

	// Graph configuration
	const nodeShape = (node: NodeDatum) => node.shape ?? GraphNodeShape.Square;
	const nodeSize = (node: NodeDatum) => node.size ?? 50;
	const nodeStrokeWidth = 3;

	// Color nodes based on type
	const nodeStroke = (node: NodeDatum) => {
		switch (node.type) {
			case 'ro':
				return '#dc2626'; // red
			case 'stakeholder':
				return '#f59e0b'; // amber
			case 'feared_event':
				return '#16a34a'; // green
			case 'asset':
				return '#0891b2'; // cyan
			default:
				return '#6b7280'; // gray
		}
	};

	const nodeFill = () => '#ffffff';

	const linkStroke = '#8FA1B9';
	const linkArrow = GraphLinkArrowStyle.Single;
	const linkArrowColor = '#4D179A';
	const linkArrowSize = 8;
	const linkFlow = true;
	const linkBandWidth = 6;
	const layoutType = GraphLayoutType.Parallel;
	const layoutParallelGroupSpacing = 250;
	const layoutParallelNodesPerColumn = 10;

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

	const nodeLabel = () => '';
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
