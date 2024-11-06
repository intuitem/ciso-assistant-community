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
			[12, 3, 22, 111, 33],
			[22, 11, 33, 11, 22]
		];

		// Calculate row totals (total for each audit)
		const auditTotals = rawData.map((audit) => audit.reduce((sum, val) => sum + val, 0));

		const grid = {
			left: 100,
			right: 100,
			top: 50,
			bottom: 50
		};

		const seriesNames = [
			'not assessed',
			'not applicable',
			'non compliant',
			'partially compliant',
			'compliant'
		];

		const series = seriesNames.map((name, categoryIdx) => {
			return {
				name,
				type: 'bar',
				stack: 'total',
				barWidth: '60%',
				label: {
					show: true,
					formatter: (params) => Math.round(params.value * 1000) / 10 + '%'
				},
				// For each audit, get this category's value divided by audit total
				data: rawData.map((audit, auditIdx) =>
					auditTotals[auditIdx] <= 0 ? 0 : audit[categoryIdx] / auditTotals[auditIdx]
				)
			};
		});

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
				data: ['audit 1', 'audit 2']
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
