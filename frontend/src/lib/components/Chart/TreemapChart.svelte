<script lang="ts">
	import { onMount } from 'svelte';
	export let s_label = '';

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name = '';
	interface treeType {
		name: string;
		children: any[];
	}
	export let tree: treeType[];

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		// specify chart configuration item and data

		var option = {
			toolbox: {
				show: true,
				feature: {
					restore: { show: true }
				}
			},
			title: {
				subtext: title
			},
			tooltip: {
				trigger: 'item',
				formatter: 'Requirements: {c}'
			},
			series: {
				type: 'treemap',
				// emphasis: {
				//     focus: 'ancestor'
				// },
				//upperLabel: {
				//	show: true
				//},
				leafDepth: 1,
				roam: false,
				visibleMin: 1,
				colorSaturation: [0.3, 0.4],
				data: tree,
				radius: [30, '95%'],
				sort: undefined,
				itemStyle: {
					borderRadius: 7,
					borderWidth: 2
				}
			}
		};

		// console.debug(option);

		// use configuration item and data specified to show chart
		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

{#if tree.length === 0}
	<div class="flex flex-col justify-center items-center h-full">
		<span class="text-center text-gray-600"
			>No enough compliance data for now. Refresh once you have more content.</span
		>
	</div>
{:else}
	<div id={chart_id} class="{width} {height} {classesContainer}" />
{/if}
