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

	export let values: any[]; // Set the types for these variables later on
	export let labels: any[];

	for (const index in values) {
		if (values[index].localName) {
			values[index].name = localItems(languageTag())[values[index].localName];
		}
	}

	let chart_element: HTMLElement | null = null;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(chart_element, null, { renderer: 'svg' });

		// specify chart configuration item and data
		let option = {
			title: {
				text: title,
				textStyle: {
					fontWeight: 'bold',
					fontSize: 14
				}
				// show: false
			},
			tooltip: {
				trigger: 'item'
			},
			legend: {
				data: ['Allocated Budget', 'Actual Spending']
			},
			radar: {
				shape: 'circle',
				indicator: labels
			},
			series: [
				{
					name: s_label,
					type: 'radar',
					data: [
						{
							value: values,
							name: 'Radar'
						}
					]
				}
			]
		};

		// console.debug(option);

		// use configuration item and data specified to show chart
		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

<div class="{width} {height} {classesContainer}" bind:this={chart_element} />
