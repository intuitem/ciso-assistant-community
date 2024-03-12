<script lang="ts">
	import { onMount } from 'svelte';
	import { localItems } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	// export let name: string;
	export let s_label: string;

	export let values: any[]; // Set the types for these variables later on
	export let colors: string[] = [];

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
			tooltip: {
				trigger: 'item'
			},
			toolbox: {
				show: true,
				feature: {
					mark: { show: true },
					dataView: { show: false, readOnly: true },
					saveAsImage: { show: false }
				}
			},
			legend: {
				top: '5%',
				left: 'center'
			},
			series: [
				{
					name: s_label,
					type: 'pie',
					radius: ['40%', '70%'],
					avoidLabelOverlap: false,
					itemStyle: {
						borderRadius: 10,
						borderColor: '#fff',
						borderWidth: 2
					},
					label: {
						show: false,
						position: 'center'
					},
					emphasis: {
						label: {
							show: true,
							fontSize: '40',
							fontWeight: 'bold'
						}
					},
					labelLine: {
						show: false
					},
					data: values,
					color: colors
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

<div class="w-auto h-full" bind:this={chart_element} />
