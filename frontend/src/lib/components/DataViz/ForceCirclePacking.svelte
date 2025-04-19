<script lang="ts">
	import { onMount } from 'svelte';
	import type * as echarts from 'echarts';
	const symbolSizeOffset = 10;
	export let width = '';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let layout = 'force';
	export let initLayout = 'circular';
	export let name = 'graph';
	export let data;
	export let color = [
		'#fc8452',
		'#ee6666',
		'#5470c6',
		'#91cc75',
		'#fac858',
		'#73c0de',
		'#3ba272',
		'#9a60b4',
		'#ea7ccc'
	];

	let searchQuery = '';
	let chart: echarts.ECharts;
	let currentEmphasisNodeId: number | null = null;
	const chart_id = `${name}_div`;
	let resizeTimeout: ReturnType<typeof setTimeout>;

	const getChartOptions = () => ({
		tooltip: {
			formatter: function (params: any) {
				const data = params.data;
				let tooltipContent = `<div style="font-style:italic; font-weight: bold;">${data.name}</div>`;

				if (data.items && Array.isArray(data.items)) {
					tooltipContent += `<div style="margin-top: 5px; border-top: 1px solid #ddd; padding-top: 5px;">
						<strong>Resulting from:</strong>
						<div style="white-space: pre-line; margin-top: 3px;">${data.items.join('<br>')}</div>
					</div>`;
				}

				return tooltipContent;
			},
			enterable: false,
			triggerOn: 'mousemove',
			backgroundColor: 'rgba(255, 255, 255, 0.95)',
			borderColor: '#ccc',
			borderWidth: 1,
			extraCssText: 'box-shadow: 0 0 3px rgba(0, 0, 0, 0.3);',
			textStyle: {
				color: '#333'
			}
		},
		title: {
			text: title,
			subtext: 'Force layout',
			top: '30',
			left: 'right'
		},
		color: color,
		series: [
			{
				type: 'graph',
				layout: layout,
				animation: false,
				zoom: 10,
				symbolSize: function (value, params) {
					// Calculate symbolSize based on node value (if exists) + symbolSizeOffset
					return (params.data.value ? params.data.value : 0) + symbolSizeOffset;
				},
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
				force: {
					layoutAnimation: true,
					initLayout: initLayout,
					gravity: 2,
					repulsion: 50,
					friction: 0.1
				},
				labelLayout: {
					hideOverlap: true
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
