<script lang="ts">
	import { onMount } from 'svelte';

	export let name: string;
	export let values: any[]; // Set this type later
	export let labels: string[];
	export let horizontal = false;
	export let title = '';

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';

	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let bar_ch = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const category = {
			type: 'category',
			data: labels,
			axisTick: {
				alignWithLabel: true
			},
			axisLabel: {
				interval: 0
			},
			position: 'right'
		};

		const value = {
			type: 'value',
			allowDecimals: false,
			minInterval: 1
		};

		// specify chart configuration item and data
		let option = {
			toolbox: {
				show: true,
				feature: {
					mark: { show: true },
					dataView: { show: false, readOnly: true },
					saveAsImage: { show: false }
				}
			},
			tooltip: {},
			title: {
				text: title,
				textStyle: {
					fontWeight: 'bold',
					fontSize: 14
				}
				// show: false
			},
			grid: { left: 0, top: 40, right: 0, bottom: 10, containLabel: true },
			xAxis: horizontal ? value : category,
			yAxis: horizontal ? category : value,
			series: [
				{
					data: values,
					type: 'bar'
				}
			]
		};

		// use configuration item and data specified to show chart
		bar_ch.setOption(option);

		window.addEventListener('resize', function () {
			bar_ch.resize();
		});

		/* bar_ch.on('click', function (params) {
      console.log('{{name}} '+params.dataIndex);
      window.open(`/browser?{{name}}=${params.dataIndex}`);
    }); */
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}" />
