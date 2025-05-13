<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = ''
	}: Props = $props();
	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart_t = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		// specify chart configuration item and data

		var option = {
			grid: { show: false },
			tooltip: {
				trigger: 'axis',
				formatter: function (params) {
					return (
						new Date(params[0].value[0]).toLocaleDateString() +
						'<br/>' +
						params[0].marker +
						params[0].seriesName +
						': ' +
						params[0].value[1]
					);
				}
			},
			xAxis: {
				type: 'time',
				splitNumber: 3,
				axisPointer: {
					snap: true
				}
			},
			yAxis: {
				type: 'value',
				boundaryGap: [0, '5%'],
				splitLine: { show: false }
			},
			series: [
				{
					name: 'Requirements assessed',
					type: 'line',
					symbol: 'none',
					areaStyle: {
						opacity: 0.8,
						color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
							{
								offset: 0,
								color: 'rgb(55, 162, 255)'
							},
							{
								offset: 1,
								color: 'rgba(55, 162, 255, 0.1)'
							}
						])
					},
					smooth: true,
					data: [
						['2024-11-22', 36],
						['2024-11-23', 37]
					]
				}
			]
		};

		chart_t.setOption(option);

		window.addEventListener('resize', function () {
			chart_t.resize();
		});
	});
</script>

<div
	id={chart_id}
	class="{height} {width} {classesContainer}"
	style="width: 400px; height:400px;"
></div>
