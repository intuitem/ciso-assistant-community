<script lang="ts">
	import { onMount } from 'svelte';

	interface treeType {
		name: string;
		children: treeType[];
	}
	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name?: string;
		tree: treeType[];
		minHeight?: string;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name = '',
		tree,
		minHeight = $bindable('100vh')
	}: Props = $props();

	function countVisibleNodes(node: treeType, maxDepth: number, depth: number = 0): number {
		if (depth >= maxDepth || !node.children || node.children.length === 0) return 1;
		let count = 1;
		for (const child of node.children) {
			count += countVisibleNodes(child, maxDepth, depth + 1);
		}
		return count;
	}

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		const LabelLayout = (await import('echarts/features')).LabelLayout;
		echarts.use([LabelLayout]);

		let chart_t = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// Count visible nodes at depth 2 to determine tree size category
		const visibleAtDepth2 = countVisibleNodes(tree as treeType, 2);
		const isLarge = visibleAtDepth2 > 200;

		// Collapse to depth 1 for large trees to avoid initial overload
		const initialTreeDepth = isLarge ? 1 : 2;

		// Recount with the actual depth we'll use for height calculation
		const actualVisible = countVisibleNodes(tree as treeType, initialTreeDepth);

		// Ensure container is tall enough: each node needs ~28px of vertical space
		const computedHeightPx = Math.max(window.innerHeight, actualVisible * 28);
		minHeight = `${computedHeightPx}px`;

		var option = {
			tooltip: {
				trigger: 'item',
				triggerOn: 'mousemove',
				formatter: function (params: any) {
					if (params.treeAncestors && params.treeAncestors.length > 0) {
						return params.treeAncestors
							.map((node: any) => node.name)
							.filter((name: string) => name)
							.join('/');
					}
					return params.name;
				}
			},
			title: { text: title },
			series: [
				{
					type: 'tree',
					roam: true,
					data: [tree],
					// Tight margins following ECharts official examples
					top: '1%',
					left: '7%',
					bottom: '1%',
					right: '20%',
					symbolSize: 7,
					symbol: 'roundRect',
					// Prevents node overlap when zooming (works on tree despite only being
					// documented for graph series)
					nodeScaleRatio: 0,
					label: {
						position: 'left',
						verticalAlign: 'middle',
						align: 'right',
						fontSize: isLarge ? 12 : 14,
						overflow: 'truncate',
						ellipsis: '...',
						width: 160
					},
					leaves: {
						label: {
							position: 'right',
							verticalAlign: 'middle',
							align: 'left'
						}
					},
					// Auto-hide labels that still overlap after layout
					labelLayout: {
						hideOverlap: true
					},
					edgeShape: 'polyline',
					edgeForkPosition: '70%',
					initialTreeDepth: initialTreeDepth,
					emphasis: {
						focus: 'descendant'
					},
					expandAndCollapse: true,
					animationDuration: 550,
					animationDurationUpdate: 750
				}
			]
		};

		chart_t.setOption(option);

		// Resize after Svelte updates the container height
		setTimeout(() => chart_t.resize(), 100);

		window.addEventListener('resize', function () {
			chart_t.resize();
		});
	});
</script>

{#if tree.length === 0}
	<div class="flex flex-col justify-center items-center h-full">
		<span class="text-center text-surface-600-400"
			>Not enough data yet. Refresh when more content is available.</span
		>
	</div>
{:else}
	<div id={chart_id} class="{height} {width} {classesContainer}"></div>
{/if}
