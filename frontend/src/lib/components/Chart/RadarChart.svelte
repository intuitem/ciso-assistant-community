<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	


	interface Props {
		// export let name: string;
		s_label?: string;
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name?: string;
		values: any[]; // Set the types for these variables later on
		labels: any[];
	}

	let {
		s_label = '',
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name = '',
		values = $bindable(),
		labels
	}: Props = $props();

	for (const index in values) {
		if (values[index].localName) {
			values[index].name = safeTranslate(values[index].localName);
		}
	}

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

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

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
