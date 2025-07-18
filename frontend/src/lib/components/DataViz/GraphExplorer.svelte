<script lang="ts">
	import { onMount } from 'svelte';
	import type * as echarts from 'echarts';

	interface Props {
		data: any;
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		layout?: string;
		initLayout?: string;
		edgeLength?: number;
		name?: string;
		zoom?: number;
		color?: any;
		maxLegendItems?: number; // New prop to control legend items
		legendPosition?: 'top' | 'bottom' | 'left' | 'right'; // New prop for legend position
	}

	let {
		data,
		width = '',
		height = 'h-full',
		classesContainer = '',
		title = '',
		layout = 'force',
		initLayout = 'circular',
		edgeLength = 50,
		name = 'graph',
		zoom = 1,
		color = [
			'#5470c6',
			'#91cc75',
			'#fac858',
			'#ee6666',
			'#73c0de',
			'#3ba272',
			'#fc8452',
			'#9a60b4',
			'#ea7ccc'
		],
		maxLegendItems = 20, // Default max legend items
		legendPosition = 'left' // Default legend position
	}: Props = $props();

	let searchQuery = $state('');
	let chart: echarts.ECharts;
	let currentEmphasisNodeId: number | null = null;
	const chart_id = `${name}_div`;
	let resizeTimeout: ReturnType<typeof setTimeout>;

	// Add custom formatter for tooltip to show custom edge label format
	// Rename to reflect that it now handles both edges and nodes
	const getCustomEdgeFormatter = () => {
		return (params) => {
			// Truncate function - truncates text to maxLength and adds ellipsis
			const truncate = (text, maxLength = 25) => {
				if (text.length <= maxLength) return text;
				return text.substring(0, maxLength) + '...';
			};

			if (params.dataType === 'edge') {
				// Find source and target node names
				const sourceNode = data.nodes.find(
					(node) => node.id === params.data.source || node.name === params.data.source
				);
				const targetNode = data.nodes.find(
					(node) => node.id === params.data.target || node.name === params.data.target
				);

				// Get labels with fallback to 'unknown'
				let sourceLabel = sourceNode ? sourceNode.name : 'unknown';
				let targetLabel = targetNode ? targetNode.name : 'unknown';
				const value = params.data.value || '';

				// Apply truncation
				sourceLabel = truncate(sourceLabel);
				targetLabel = truncate(targetLabel);

				// Return formatted label with src and tgt in bold, value in italic
				return `<b>${sourceLabel}</b> - <i>${value}</i> - <b>${targetLabel}</b>`;
			} else if (params.dataType === 'node') {
				// For nodes, truncate the name
				const nodeName = params.name || params.data.name || 'unnamed';
				const truncatedName = truncate(nodeName);

				// You can add additional node properties here if needed
				return `<b>${truncatedName}</b>`;
			}

			return params.name;
		};
	};

	// Function to get legend configuration based on number of categories
	const getLegendConfig = () => {
		const categories = data.categories || [];
		const hasMany = categories.length > maxLegendItems;

		// Base legend configuration
		const legendConfig = {
			data: categories.map(function (a) {
				return a.name;
			}),
			type: hasMany ? 'scroll' : 'plain', // Use scroll type for many items
			orient: legendPosition === 'left' || legendPosition === 'right' ? 'vertical' : 'horizontal',
			...getLegendPositioning()
		};

		// Add scroll configuration if needed
		if (hasMany) {
			if (legendPosition === 'top' || legendPosition === 'bottom') {
				legendConfig.scrollDataIndex = 0;
				legendConfig.pageButtonItemGap = 5;
				legendConfig.pageButtonGap = 30;
				legendConfig.pageButtonPosition = 'end';
				legendConfig.pageFormatter = '{current}/{total}';
				legendConfig.pageIconColor = '#2f4554';
				legendConfig.pageIconInactiveColor = '#aaa';
				legendConfig.pageIconSize = 15;
				legendConfig.pageTextStyle = {
					color: '#666'
				};
			} else {
				// For vertical legends, limit height
				legendConfig.height = '60%';
			}
		}

		return legendConfig;
	};

	// Function to get legend positioning based on legendPosition prop
	const getLegendPositioning = () => {
		switch (legendPosition) {
			case 'top':
				return {
					top: 10,
					left: 'center'
				};
			case 'bottom':
				return {
					bottom: 10,
					left: 'center'
				};
			case 'left':
				return {
					left: 10,
					top: 'middle'
				};
			case 'right':
				return {
					right: 10,
					top: 'middle'
				};
			default:
				return {
					top: 10,
					left: 'center'
				};
		}
	};

	// Function to calculate dynamic spacing based on legend and title
	const calculateSpacing = () => {
		const categories = data.categories || [];
		const hasMany = categories.length > maxLegendItems;
		const hasTitle = title && title.trim().length > 0;

		// Calculate legend height/width based on position and items
		let legendSpace = 0;
		if (legendPosition === 'top' || legendPosition === 'bottom') {
			// For horizontal legends, calculate based on wrapping
			const itemsPerRow = Math.floor(12); // Approximate items per row
			const rows = Math.ceil(Math.min(categories.length, maxLegendItems) / itemsPerRow);
			legendSpace = hasMany ? 60 : Math.max(30, rows * 25);
		} else {
			// For vertical legends
			legendSpace = hasMany ? 200 : 150;
		}

		// Title space
		const titleSpace = hasTitle ? 60 : 20;

		return { legendSpace, titleSpace };
	};

	const getChartOptions = () => {
		const { legendSpace, titleSpace } = calculateSpacing();

		return {
			legend: getLegendConfig(),
			tooltip: {
				formatter: getCustomEdgeFormatter(),
				label: {
					position: 'right',
					show: true
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
				top: legendPosition === 'top' ? legendSpace + 10 : 10,
				left: 'right'
			},
			color: color,
			series: [
				{
					type: 'graph',
					layout: layout,
					symbolSize: 20,
					animation: false,
					zoom: zoom,
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
					// Add explicit positioning for the graph
					top: legendPosition === 'top' ? legendSpace + titleSpace : titleSpace,
					bottom: legendPosition === 'bottom' ? legendSpace + 20 : 20,
					left: legendPosition === 'left' ? legendSpace + 20 : 20,
					right: legendPosition === 'right' ? legendSpace + 20 : 20,
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
					edgeLabel: {
						show: false // Hide permanent edge labels
					},
					edges: data.links,
					lineStyle: {
						curveness: 0.2,
						color: 'source',
						width: 1.5
					}
				}
			]
		};
	};

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
		class="w-full rounded-md border-gray-200 py-2.5 pe-10 shadow-xs"
		bind:value={searchQuery}
		onkeydown={handleKeyDown}
		placeholder="Find a node ..."
	/>
	<span class="absolute inset-y-0 end-0 grid w-10 place-content-center">
		<button
			type="button"
			class="text-gray-600 hover:text-gray-700"
			onclick={() => searchNode(searchQuery)}
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
<div id={chart_id} class="{width} {height} {classesContainer} p-8" role="presentation"></div>
