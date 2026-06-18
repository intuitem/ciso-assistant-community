<script lang="ts">
	import { VisSingleContainer, VisGraph } from '@unovis/svelte';
	import { GraphLayoutType, GraphNodeShape, GraphLinkArrowStyle } from '@unovis/ts';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	type NodeDatum = {
		id: string;
		label: string;
		type: 'ro' | 'to' | 'stakeholder' | 'asset' | 'feared_event';
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
		height = '700px',
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
					label: safeTranslate(path.risk_origin),
					type: 'ro',
					shape: GraphNodeShape.Circle,
					size: 70
				});
				nodeIds.add(`ro-${path.risk_origin}`);
			}
		});

		// Column 2: Add Target Objective nodes
		attackPaths.forEach((path) => {
			if (path.target_objective && !nodeIds.has(`to-${path.target_objective}`)) {
				nodes.push({
					id: `to-${path.target_objective}`,
					label: safeTranslate(path.target_objective),
					type: 'to',
					shape: GraphNodeShape.Hexagon,
					size: 70
				});
				nodeIds.add(`to-${path.target_objective}`);
			}

			// Link RO → TO
			if (path.risk_origin && path.target_objective) {
				links.push({
					source: `ro-${path.risk_origin}`,
					target: `to-${path.target_objective}`
				});
			}
		});

		// Column 3: Add Stakeholder (Ecosystem) nodes
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

				// Link TO → Stakeholder
				if (path.target_objective) {
					const linkId = `${path.target_objective}-${stakeholder.id}`;
					if (!links.find((l) => `${l.source}-${l.target}` === linkId)) {
						links.push({
							source: `to-${path.target_objective}`,
							target: nodeId
						});
					}
				}
			});
		});

		// Column 4: Add Feared Event nodes
		fearedEvents.forEach((fearedEvent) => {
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
		});

		// Link Stakeholders → Feared Events OR TO → Feared Events (if no stakeholders)
		attackPaths.forEach((path) => {
			if (path.stakeholders && path.stakeholders.length > 0) {
				// If there are stakeholders: Stakeholders → Feared Events
				path.stakeholders.forEach((stakeholder) => {
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
			} else if (path.target_objective) {
				// If NO stakeholders: TO → Feared Events directly
				fearedEvents.forEach((fearedEvent) => {
					const linkId = `to-${path.target_objective}-${fearedEvent.id}`;
					if (!links.find((l) => `${l.source}-${l.target}` === linkId)) {
						links.push({
							source: `to-${path.target_objective}`,
							target: `fe-${fearedEvent.id}`
						});
					}
				});
			}
		});

		// Column 5: Add Asset nodes
		const assetIds = new Set<string>();
		fearedEvents.forEach((fearedEvent) => {
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
					assetIds.add(asset.id);
				}

				// Link Feared Events → Assets
				links.push({
					source: `fe-${fearedEvent.id}`,
					target: assetNodeId
				});
			});
		});

		return { nodes, links };
	});

	// Build panels for layout with 5 columns
	const panels = $derived([
		{
			label: m.riskOrigins(),
			nodes: graphData.nodes.filter((n) => n.type === 'ro').map((n) => n.id),
			padding: { top: 60, right: 60, bottom: 60, left: 60 },
			dashedOutline: true,
			borderColor: '#dc2626',
			sideIconSymbol: '&#xf071;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#dc2626'
		},
		{
			label: m.targetObjectives(),
			nodes: graphData.nodes.filter((n) => n.type === 'to').map((n) => n.id),
			padding: { top: 60, right: 60, bottom: 60, left: 60 },
			dashedOutline: true,
			borderColor: '#a855f7',
			sideIconSymbol: '&#xf140;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#a855f7'
		},
		{
			label: m.studyTheEcosystem(),
			nodes: graphData.nodes.filter((n) => n.type === 'stakeholder').map((n) => n.id),
			padding: { top: 60, right: 60, bottom: 60, left: 60 },
			dashedOutline: true,
			borderColor: '#f59e0b',
			sideIconSymbol: '&#xf0c0;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#f59e0b'
		},
		{
			label: m.fearedEvents(),
			nodes: graphData.nodes.filter((n) => n.type === 'feared_event').map((n) => n.id),
			padding: { top: 60, right: 60, bottom: 60, left: 60 },
			dashedOutline: true,
			borderColor: '#16a34a',
			sideIconSymbol: '&#xf530;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#16a34a'
		},
		{
			label: m.assets(),
			nodes: graphData.nodes.filter((n) => n.type === 'asset').map((n) => n.id),
			padding: { top: 60, right: 60, bottom: 60, left: 60 },
			dashedOutline: true,
			borderColor: '#0891b2',
			sideIconSymbol: '&#xf1b2;',
			sideIconShape: 'circle',
			sideIconSymbolColor: '#0891b2'
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
			case 'to':
				return '#a855f7'; // purple
			case 'stakeholder':
				return '#f59e0b'; // amber
			case 'asset':
				return '#0891b2'; // cyan
			case 'feared_event':
				return '#16a34a'; // green
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
	const layoutParallelGroupSpacing = 300;
	const layoutParallelNodesPerColumn = 8;

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

<div class="chart bg-surface-50-950 rounded-lg shadow-sm">
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
			zoomScaleExtent={[0.3, 1.25]}
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
