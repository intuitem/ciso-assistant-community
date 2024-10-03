<script lang="ts">
	import { onMount } from 'svelte';

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name = '';
	interface treeType {
		name: string;
		children: treeType[];
	}
	export let tree: treeType[];

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart_t = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		// specify chart configuration item and data

		var option = {
			tooltip: {
				trigger: 'item',
				triggerOn: 'mousemove'
			},
			title: { text: title },
			series: [
				{
					type: 'tree',

					data: [tree],
					symbol: 'emptyCircle',
					symbolSize: 10,

					label: {
						position: 'left',
						verticalAlign: 'middle',
						align: 'right',
						fontSize: 10
					},

					leaves: {
						label: {
							position: 'right',
							verticalAlign: 'middle',
							align: 'left'
						}
					},

					emphasis: {
						focus: 'descendant'
					},

					expandAndCollapse: true,
					animationDuration: 550,
					animationDurationUpdate: 750
				}
			]
		};

		// console.debug(option);

		// use configuration item and data specified to show chart
		chart_t.setOption(option);

		window.addEventListener('resize', function () {
			chart_t.resize();
		});
	});
</script>

{#if tree.length === 0}
	<div class="flex flex-col justify-center items-center h-full">
		<span class="text-center text-gray-600"
			>Not enough data yet. Refresh when more content is available.</span
		>
	</div>
{:else}
	<div id={chart_id} class="{height} {width} {classesContainer}" />
{/if}
