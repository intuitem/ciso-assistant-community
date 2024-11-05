<script lang="ts">
	import { onMount } from 'svelte';
	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name = '';

	interface sankeyData {
		source: string;
		target: string;
		value: number;
	}
	export let values: sankeyData[]; // Set the types for these variables later on

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data
		const rawData = [
			[100, 302, 301, 334, 390, 330, 320],
			[320, 132, 101, 134, 90, 230, 210],
			[220, 182, 191, 234, 290, 330, 310],
			[150, 212, 201, 154, 190, 330, 410],
			[820, 832, 901, 934, 1290, 1330, 1320]
		];
		const totalData = [];
		for (let i = 0; i < rawData[0].length; ++i) {
			let sum = 0;
			for (let j = 0; j < rawData.length; ++j) {
				sum += rawData[j][i];
			}
			totalData.push(sum);
		}
		const grid = {
			left: 100,
			right: 100,
			top: 50,
			bottom: 50
		};
		const series = ['Direct', 'Mail Ad', 'Affiliate Ad', 'Video Ad', 'Search Engine'].map(
			(name, sid) => {
				return {
					name,
					type: 'bar',
					stack: 'total',
					barWidth: '60%',
					label: {
						show: true,
						formatter: (params) => Math.round(params.value * 1000) / 10 + '%'
					},
					data: rawData[sid].map((d, did) => (totalData[did] <= 0 ? 0 : d / totalData[did]))
				};
			}
		);
		var option = {
			legend: {
				selectedMode: false
			},
			grid,
			yAxis: {
				type: 'value'
			},
			xAxis: {
				type: 'category',
				data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
			},
			series
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
