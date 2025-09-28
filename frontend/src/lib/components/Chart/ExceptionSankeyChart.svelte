<script lang="ts">
	import { onMount } from 'svelte';

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
				triggerOn: 'mousemove'
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

		window.addEventListener('resize', function () {
			chart.resize();
		});

		// Cleanup function
		return () => {
			chart.dispose();
			window.removeEventListener('resize', () => chart.resize());
		};
	});
</script>

<div id={chart_id} class="{height} {width} {classesContainer}" style="width: 100%; height: 100%;"></div>
