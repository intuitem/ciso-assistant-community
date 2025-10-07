<script lang="ts">
	import { onMount } from 'svelte';

	interface Series {
		name: string;
		data: number[];
	}

	interface Props {
		name: string;
		title?: string;
		categories: string[];
		series: Series[];
		width?: string;
		height?: string;
		classesContainer?: string;
	}

	let {
		name,
		title = '',
		categories,
		series,
		width = 'w-auto',
		height = 'h-full',
		classesContainer = ''
	}: Props = $props();

	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const option = {
			title: {
				text: title,
				textStyle: {
					fontWeight: 'bold',
					fontSize: 14
				}
			},
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow'
				}
			},
			legend: {
				bottom: 0,
				left: 'center'
			},
			grid: {
				left: 0,
				top: 40,
				right: 0,
				bottom: 40,
				containLabel: true
			},
			xAxis: {
				type: 'category',
				data: categories,
				axisTick: {
					alignWithLabel: true
				},
				axisLabel: {
					interval: 0,
					rotate: 0
				}
			},
			yAxis: {
				type: 'value',
				allowDecimals: false,
				minInterval: 1
			},
			series: series.map((s) => ({
				name: s.name,
				type: 'bar',
				data: s.data,
				emphasis: {
					focus: 'series'
				}
			}))
		};

		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
