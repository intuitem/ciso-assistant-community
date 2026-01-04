<script lang="ts">
	import { onMount } from 'svelte';

	import { safeTranslate } from '$lib/utils/i18n';

	import { level } from '$paraglide/messages';
	interface riskChartData {
		name: string;
		value: number;
		color: string;
	}

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name: string;
		values: riskChartData[]; // Set the types for these variables later on
		colors?: string[];
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name,
		values = $bindable(),
		colors = []
	}: Props = $props();

	for (const index in values) {
		if (values[index].name) {
			values[index].name = safeTranslate(values[index].name);
		}
	}
	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data
		var option = {
			title: {
				subtext: title
			},
			tooltip: {
				trigger: 'item'
			},
			series: [
				{
					name: level(),
					type: 'pie',
					radius: ['40%', '70%'],
					center: ['50%', '70%'],
					// adjust the start and end angle
					startAngle: 180,
					endAngle: 360,
					minShowLabelAngle: 1,
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

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
