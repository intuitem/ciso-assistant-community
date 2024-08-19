<script lang="ts">
	import { onMount } from 'svelte';
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	// export let name: string;
	export let s_label = '';

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name = '';

	export let tree: any[];

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		var data = tree;
		// specify chart configuration item and data
		function getLevelOption() {
			return [
				{
					itemStyle: {
						borderColor: '#777',
						borderWidth: 0,
						gapWidth: 1
					},
					upperLabel: {
						show: false
					}
				},
				{
					itemStyle: {
						borderColor: '#555',
						borderWidth: 5,
						gapWidth: 1
					},
					emphasis: {
						itemStyle: {
							borderColor: '#ddd'
						}
					}
				},
				{
					colorSaturation: [0.35, 0.5],
					itemStyle: {
						borderWidth: 5,
						gapWidth: 1,
						borderColorSaturation: 0.6
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
				//levels: getLevelOption(),
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
