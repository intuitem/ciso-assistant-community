<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface SunburstData {
		name: string;
		value?: number;
		children?: SunburstData[];
		itemStyle?: {
			color?: string;
		};
	}

	interface Props {
		name: string;
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		data: SunburstData[];
	}

	let {
		name,
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		data = []
	}: Props = $props();

	// Auto-translate node names recursively
	function translateData(nodes: SunburstData[]): SunburstData[] {
		return nodes.map((node) => {
			const translatedNode = { ...node };

			// Note: Node name translation removed to use m.stringKey() pattern in tooltip only

			// Recursively translate children
			if (translatedNode.children) {
				translatedNode.children = translateData(translatedNode.children);
			}

			return translatedNode;
		});
	}

	const translatedData = translateData(data);
	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const option = {
			title: {
				text: title,
				left: 'center',
				textStyle: {
					fontWeight: 'bold',
					fontSize: 14
				}
			},
			tooltip: {
				trigger: 'item',
				backgroundColor: 'rgba(50, 50, 50, 0.9)',
				borderColor: '#777',
				borderWidth: 1,
				textStyle: {
					color: '#fff',
					fontSize: 12
				},
				formatter: function (params: any) {
					const ancestry = [];
					let currentData = params.data;

					// Build the path from root to current node
					while (currentData) {
						ancestry.unshift(currentData.name);
						currentData = currentData.parent;
					}

					const path = ancestry.join(' → ');
					const count = params.data.value || 0;
					const percentage = params.percent ? `${params.percent.toFixed(1)}%` : '';

					return `
						<div style="max-width: 300px; word-wrap: break-word;">
							<strong>${m.pathLabel()}:</strong><br/>
							${path}<br/>
							<strong>${m.countLabel()}:</strong> ${count} ${m.controlsLabel()}
							${percentage ? `<br/><strong>${m.percentage()}:</strong> ${percentage}` : ''}
						</div>
					`;
				}
			},
			series: {
				type: 'sunburst',
				data: translatedData,
				radius: [0, '90%'],
				center: ['50%', '50%'],
				sort: undefined,
				emphasis: {
					focus: 'ancestor'
				},
				levels: [
					{
						// Root level - no labels to avoid clutter
						label: {
							show: false
						}
					},
					{
						// Level 1: Domains/Folders
						r0: '10%',
						r: '30%',
						itemStyle: {
							borderWidth: 3,
							borderColor: '#fff'
						},
						label: {
							show: true,
							fontSize: 12,
							fontWeight: 'bold',
							color: '#333',
							rotate: 'radial',
							align: 'center',
							minAngle: 10 // Only show labels if segment is large enough
						}
					},
					{
						// Level 2: CSF Functions
						r0: '30%',
						r: '50%',
						itemStyle: {
							borderWidth: 2,
							borderColor: '#fff'
						},
						label: {
							show: true,
							fontSize: 10,
							color: '#555',
							rotate: 'tangential',
							minAngle: 15 // Only show labels if segment is large enough
						}
					},
					{
						// Level 3: Categories
						r0: '50%',
						r: '70%',
						itemStyle: {
							borderWidth: 2,
							borderColor: '#fff'
						},
						label: {
							show: true,
							fontSize: 9,
							color: '#666',
							rotate: 'tangential',
							minAngle: 20 // Only show labels if segment is large enough
						}
					},
					{
						// Level 4: Priority
						r0: '70%',
						r: '85%',
						itemStyle: {
							borderWidth: 2,
							borderColor: '#fff'
						},
						label: {
							show: true,
							fontSize: 8,
							color: '#777',
							rotate: 'tangential',
							minAngle: 25 // Only show labels if segment is large enough
						}
					},
					{
						// Level 5: Status (outermost)
						r0: '85%',
						r: '95%',
						itemStyle: {
							borderWidth: 1,
							borderColor: '#fff'
						},
						label: {
							show: true,
							fontSize: 7,
							color: '#888',
							rotate: 'tangential',
							minAngle: 30 // Only show labels if segment is large enough
						}
					}
				]
			}
		};

		chart.setOption(option);

		const resizeHandler = function () {
			chart.resize();
		};

		window.addEventListener('resize', resizeHandler);

		// Cleanup function
		return () => {
			if (chart) {
				chart.dispose();
			}
			window.removeEventListener('resize', resizeHandler);
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
