<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { show } from '$paraglide/messages/pt';
	import { axis } from '@unovis/ts/components/axis/style';

	// export let name: string;
	export let s_label = '';

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name = '';

	export let values: any[]; // Set the types for these variables later on
	export let labels: any[];

	const axisVal = 16;

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
			xAxis: {
				min: -axisVal,
				max: axisVal,
				type: 'value',
				axisLabel: { show: false },
				axisTick: { show: false }
			},
			yAxis: {
				min: -axisVal,
				max: axisVal,
				type: 'value',
				axisLabel: { show: false },
				axisTick: { show: false }
			},
			series: [
				{
					symbolSize: 20,
					data: [
						[3, 4],
						[-3, 2],
						[-3, -4],
						[-2, 4]
					],
					type: 'scatter'
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

<div id={chart_id} class="{width} {height} {classesContainer}" />
