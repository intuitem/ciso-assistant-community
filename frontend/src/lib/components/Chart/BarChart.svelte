<script lang="ts">
	import { onMount } from 'svelte';

	export let name: string;
	export let values: any[]; // Set this type later
	export let labels: string[];

	$: chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let bar_ch = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data
		let option = {
			toolbox: {
				show: true,
				feature: {
					mark: { show: true },
					dataView: { show: false, readOnly: true },
					saveAsImage: { show: true }
				}
			},
			tooltip: {},
			xAxis: {
				type: 'category',
				data: labels,
				axisTick: {
					alignWithLabel: true
				}
			},
			yAxis: {
				type: 'value',
				allowDecimals: false,
				minInterval: 1
			},
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

<div id={chart_id} class="bg-white w-auto h-full" />
