<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import { onMount } from 'svelte';
	let searchQuery = ''; // Search query for the node name
	export let width = '';
	export let height = 'h-screen';
	export let classesContainer = '';
	export let name = 'graph';
	const chart_id = `${name}_div`;
	import { pageTitle } from '$lib/utils/stores';
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id));
		let currentEmphasisNodeId: number | null = null;
		pageTitle.set(data.data.meta.display_name);

		// specify chart configuration item and data
		var option = {
			legend: [
				{
					// selectedMode: 'single',
					data: data.data.categories.map(function (a) {
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
				text: 'Mapping explorer',
				subtext: 'Force layout',
				top: 'top',
				left: 'right'
			},
			series: [
				{
					type: 'graph',
					layout: 'force',
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
					data: data.data.nodes.map(function (node, idx) {
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
					categories: data.data.categories,
					force: {
						edgeLength: 50,
						repulsion: 50,
						gravity: 0.1,
						layoutAnimation: true,
						friction: 0.1,
						initLayout: 'circular'
					},
					labelLayout: {
						hideOverlap: true
					},
					edges: data.data.links,
					lineStyle: {
						curveness: 0.2,
						color: 'source'
					}
				}
			]
		};

		// use configuration item and data specified to show chart
		chart.hideLoading();
		chart.setOption(option);

		// Handle click events
		chart.on('click', function (params) {
			if (params.dataType === 'node') {
				// If clicking the same node, deselect it
				if (currentEmphasisNodeId === params.data.id) {
					chart.dispatchAction({
						type: 'downplay',
						dataIndex: currentEmphasisNodeId
					});
					currentEmphasisNodeId = -1;
				} else {
					// Downplay previously selected node
					if (currentEmphasisNodeId !== -1) {
						chart.dispatchAction({
							type: 'downplay',
							dataIndex: currentEmphasisNodeId
						});
					}
					// Highlight the clicked node and show labels of adjacent nodes
					chart.dispatchAction({
						type: 'highlight',
						dataIndex: params.data.id
					});
					currentEmphasisNodeId = params.data.id;
				}
			} else {
				// If clicking outside nodes, remove emphasis
				if (currentEmphasisNodeId !== -1) {
					chart.dispatchAction({
						type: 'downplay',
						dataIndex: currentEmphasisNodeId
					});
					currentEmphasisNodeId = -1;
				}
			}
		}); // Function to search and highlight node
		const searchNode = (query: string) => {
			// Find node by name
			const node = data.data.nodes.find((n) => n.name.toLowerCase() === query.toLowerCase());
			if (node) {
				// Downplay previously highlighted node
				if (currentEmphasisNodeId !== -1) {
					chart.dispatchAction({
						type: 'downplay',
						dataIndex: currentEmphasisNodeId
					});
				}

				// Highlight the found node
				chart.dispatchAction({
					type: 'highlight',
					dataIndex: node.id
				});
				currentEmphasisNodeId = node.id;
			} else {
				alert('Node not found!');
			}
		};

		// Attach the search function to make it accessible
		window.searchNode = searchNode;

		// Handle window resize
		const handleResize = () => {
			chart.resize();
		};
		window.addEventListener('resize', handleResize);

		// Cleanup on component destruction
		return () => {
			window.removeEventListener('resize', handleResize);
			chart.dispose();
		};
	});
</script>

<div class="relative p-2">
	<label for="Search" class="sr-only"> Search </label>
	<input
		type="text"
		class="w-full rounded-md border-gray-200 py-2.5 pe-10 shadow-sm"
		bind:value={searchQuery}
		placeholder="Search a requirement by id ..."
		on:keydown={(event) => {
			if (event.key === 'Enter') searchNode(searchQuery);
		}}
	/>
	<span class="absolute inset-y-0 end-0 grid w-10 place-content-center">
		<button class="text-gray-600 hover:text-gray-700" on:click={() => searchNode(searchQuery)}>
			<span class="sr-only">Search</span>
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
			</svg></button
		>
	</span>
</div>
<div id={chart_id} class="{width} {height} {classesContainer} p-8" />
