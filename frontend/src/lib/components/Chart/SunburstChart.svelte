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
		function getLevelOption() {
			return [
				{
					itemStyle: {
						borderWidth: 0,
						gapWidth: 1
					},
					upperLabel: {
						show: false
					},
					label: {
						rotate: 'tangential'
					}
				},
				{
					itemStyle: {
						borderWidth: 5,
						gapWidth: 1
					},
					label: {
						rotate: 'tangential'
					},
					emphasis: {
						itemStyle: {}
					}
				},
				{
					itemStyle: {
						borderWidth: 5,
						gapWidth: 1
					},
					label: {
						rotate: 'tangential'
					},
					emphasis: {
						itemStyle: {}
					}
				}
			];
		}
		var option = {
			title: {
				subtext: title
			},
			series: {
				type: 'sunburst',
				// emphasis: {
				//     focus: 'ancestor'
				// },
				//upperLabel: {
				//	show: true
				//},
				levels: getLevelOption(),
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

<div id={chart_id} class="{width} {height} {classesContainer}" />
