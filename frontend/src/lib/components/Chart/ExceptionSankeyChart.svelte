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
		name = 'exception_sankey',
		nodes = [],
		links = []
	}: Props = $props();

	// Auto-translate node names for severity and status values
	for (const node of nodes) {
		if (node.name) {
			// Handle patterns like "Severity: Critical" or "Status: New"
			const parts = node.name.split(': ');
			if (parts.length === 2) {
				const [prefix, value] = parts;
				const translatedPrefix = safeTranslate(prefix.toLowerCase());
				const translatedValue = safeTranslate(value.toLowerCase());
				node.name = `${translatedPrefix}: ${translatedValue}`;
			}
		}
	}

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
						const sourceNode = nodes[params.data.source];
						const targetNode = nodes[params.data.target];
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
					data: nodes,
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
					draggable: false,
					focusNodeAdjacency: true,
					levels: [
						{
							depth: 0,
							itemStyle: {
								color: '#3B82F6'
							}
						},
						{
							depth: 1,
							itemStyle: {
								color: '#10B981'
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
