<script lang="ts">
	import { onMount } from 'svelte';
	import type * as echarts from 'echarts';

	export let data;
	export let width = '';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let layout = 'force';
	export let initLayout = 'circular';
	export let edgeLength = 50;
	export let name = 'graph';

	let searchQuery = '';
	let chart: echarts.ECharts;
	let currentEmphasisNodeId: number | null = null;
	const chart_id = `${name}_div`;
	let resizeTimeout: ReturnType<typeof setTimeout>;

	const getChartOptions = () => ({
		legend: [
			{
				data: data.categories.map(function (a) {
					return a.name;
				})
			}
		],
		tooltip: {
			label: {
				position: 'right',
				show: true
			}
		},
		title: {
			text: title,
			subtext: 'Force layout',
			top: '30',
			left: 'right'
		},
		series: [
			{
				type: 'graph',
				layout: layout,
				symbolSize: 20,
				animation: false,
				animationDurationUpdate: 1500,
				animationEasingUpdate: 'quinticInOut',
				edgeSymbol: ['circle', 'arrow'],
				label: {
					position: 'right',
					formatter: '{b}',
					show: false
				},
				draggable: true,
				roam: true,
				data: data.nodes.map(function (node, idx) {
					node.id = idx;
					return node;
				}),
				emphasis: {
					focus: 'adjacency',
					label: {
						position: 'right',
						show: true
					}
				},
				selectedMode: 'series',
				select: {
					itemStyle: {
						borderColor: '#666',
						borderWidth: 2
					},
					label: {
						show: true
					}
				},
				categories: data.categories,
				force: {
					edgeLength: edgeLength,
					repulsion: 200,
					gravity: 0.05,
					layoutAnimation: true,
					friction: 0.1,
					initLayout: initLayout
				},
				labelLayout: {
					hideOverlap: true
				},
				edges: data.links,
				lineStyle: {
					curveness: 0.2,
					color: 'source'
				}
			}
		]
	});

	const handleNodeEmphasis = (nodeId: number | null) => {
		if (!chart) return;

		if (currentEmphasisNodeId !== null) {
			chart.dispatchAction({
				type: 'downplay',
				dataIndex: currentEmphasisNodeId
			});
		}

		if (nodeId !== null && nodeId !== currentEmphasisNodeId) {
			chart.dispatchAction({
				type: 'highlight',
				dataIndex: nodeId
			});
		}

		currentEmphasisNodeId = nodeId !== currentEmphasisNodeId ? nodeId : null;
	};

	// Search function, maybe we can improve it later for fuzzy search?
	const searchNode = (query: string) => {
		if (!query.trim()) return;

		const normalizedQuery = query.toLowerCase().trim();
		const node = data.nodes.find((n) => n.name.toLowerCase().includes(normalizedQuery));

		if (node && node.id !== undefined) {
			handleNodeEmphasis(node.id);
			chart?.dispatchAction({
				type: 'focusNodeAdjacency',
				dataIndex: node.id
			});
		} else {
			alert('No matching nodes found');
		}
	};

	onMount(async () => {
		const echarts = await import('echarts');
		const element = document.getElementById(chart_id);

		if (!element) {
			console.error(`Element with id ${chart_id} not found`);
			return;
		}

		chart = echarts.init(element);
		const options = getChartOptions();
		chart.setOption(options);

		chart.on('click', (params) => {
			if (params.dataType === 'node') {
				handleNodeEmphasis(params.data.id);
			} else {
				handleNodeEmphasis(null);
			}
		});

		const handleResize = () => {
			clearTimeout(resizeTimeout);
			resizeTimeout = setTimeout(() => {
				chart?.resize();
			}, 250);
		};

		window.addEventListener('resize', handleResize);

		return () => {
			window.removeEventListener('resize', handleResize);
			clearTimeout(resizeTimeout);
			chart?.dispose();
		};
	});

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Enter') {
			searchNode(searchQuery);
		}
	};
</script>

<div class="relative p-2">
	<label for="graph-search" class="sr-only">Search</label>
	<input
		id="graph-search"
		type="text"
		class="w-full rounded-md border-gray-200 py-2.5 pe-10 shadow-sm"
		bind:value={searchQuery}
		on:keydown={handleKeyDown}
		placeholder="Find a node ..."
	/>
	<span class="absolute inset-y-0 end-0 grid w-10 place-content-center">
		<button
			type="button"
			class="text-gray-600 hover:text-gray-700"
			on:click={() => searchNode(searchQuery)}
			aria-label="Search"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="size-4"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
				/>
			</svg>
		</button>
	</span>
</div>
<div id={chart_id} class="{width} {height} {classesContainer} p-8" role="presentation" />
