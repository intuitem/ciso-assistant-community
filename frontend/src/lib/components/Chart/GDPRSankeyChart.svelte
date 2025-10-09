<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	interface SankeyNode {
		name: string;
	}

	interface SankeyLink {
		source: number;
		target: number;
		value: number;
	}

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name?: string;
		nodes: SankeyNode[];
		links: SankeyLink[];
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name = 'gdpr_sankey',
		nodes = [],
		links = []
	}: Props = $props();

	// Translate node names - handle "Processing: name", "LegalBasis: basis" patterns
	const translatedNodes = nodes.map((node) => {
		if (node.name) {
			const parts = node.name.split(': ');
			if (parts.length === 2) {
				const [prefix, value] = parts;
				// For Legal basis, use camelCase key for translation
				if (prefix === 'LegalBasis') {
					const translatedPrefix = safeTranslate('legalBasis');
					const translatedValue = safeTranslate(value.toLowerCase());
					return { ...node, name: `${translatedPrefix}: ${translatedValue}` };
				}
				// For Processing, translate prefix
				const translatedPrefix = safeTranslate(prefix.toLowerCase());
				return { ...node, name: `${translatedPrefix}: ${value}` };
			}
			// No prefix - translate directly (for PD categories)
			const translatedName = safeTranslate(node.name.toLowerCase());
			return { ...node, name: translatedName };
		}
		return node;
	});

	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const option = {
			title: {
				text: title,
				left: 'center',
				textStyle: {
					fontSize: 16,
					fontWeight: 'bold'
				}
			},
			tooltip: {
				trigger: 'item',
				triggerOn: 'mousemove',
				formatter: function (params) {
					if (params.dataType === 'edge') {
						// For links/flows, get node names by index
						const sourceNode = translatedNodes[params.data.source];
						const targetNode = translatedNodes[params.data.target];
						return `${sourceNode.name} → ${targetNode.name}<br/>Count: ${params.value}`;
					} else {
						// For nodes, show the node name and its total count
						return `${params.name}<br/>Count: ${params.value}`;
					}
				}
			},
			series: [
				{
					type: 'sankey',
					data: translatedNodes,
					links: links,
					emphasis: {
						focus: 'adjacency'
					},
					lineStyle: {
						color: 'gradient',
						curveness: 0.5
					},
					layoutIterations: 10,
					orient: 'horizontal',
					draggable: true,
					focusNodeAdjacency: true,
					nodeWidth: 30,
					nodeGap: 15,
					levels: [
						{
							depth: 0,
							itemStyle: {
								color: '#3B82F6' // Personal Data - Blue
							}
						},
						{
							depth: 1,
							itemStyle: {
								color: '#8B5CF6' // Processing - Purple
							}
						},
						{
							depth: 2,
							itemStyle: {
								color: '#10B981' // Legal Basis - Green
							}
						}
					]
				}
			]
		};

		chart.setOption(option);

		const resizeHandler = function () {
			chart.resize();
		};

		window.addEventListener('resize', resizeHandler);

		// Cleanup function
		return () => {
			chart.dispose();
			window.removeEventListener('resize', resizeHandler);
		};
	});
</script>

<div
	id={chart_id}
	class="{height} {width} {classesContainer}"
	style="width: 100%; height: 100%;"
></div>
