<script lang="ts">
	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	// export let name: string;

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = 'border';
	export let title = '';
	export let name = '';
	export let data;

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		const getGraphicElements = (chart) => {
			const chartWidth = chart.getWidth();
			const chartHeight = chart.getHeight();

			return [
				// Existing text elements
				{
					type: 'text',
					position: [(3 * chartWidth) / 4, (3 * chartHeight) / 4],
					silent: true,
					style: {
						text: 'P4 (' + data.priority_cnt.p4 + ')',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				},
				{
					type: 'text',
					position: [chartWidth / 4, (3 * chartHeight) / 4],
					silent: true,
					style: {
						text: 'P3 (' + data.priority_cnt.p3 + ')',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				},
				{
					type: 'text',
					position: [(3 * chartWidth) / 4, chartHeight / 4],
					silent: true,
					style: {
						text: 'P2 (' + data.priority_cnt.p2 + ')',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				},
				{
					type: 'text',
					position: [chartWidth / 4, chartHeight / 4],
					silent: true,
					style: {
						text: 'P1 (' + data.priority_cnt.p1 + ')',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				}
			];
		};
		//TODO use the safetranslate on formatter
		const option = {
			title: {
				text: 'Displaying prioritized non-active controls',
				subtext: 'Click here to review the non-prioritized ones',
				sublink: '/applied-controls?priority=null'
			},
			color: ['#4D4870', '#74C0DE', '#FAB746', '#8B5DF6', '#f87171'],
			graphic: getGraphicElements(chart),
			legend: {
				data: ['--', 'To do', 'In progress', 'On hold', 'Deprecated'],
				top: 60
			},
			polar: {},
			tooltip: {
				formatter: function (params) {
					if (params.value[0] >= 100) {
						return (
							params.value[3] +
							'<br/>Links: <br/><i>ETA not set or beyond 100 days</i><br/>' +
							params.value[4]
						);
					}
					return (
						params.value[3] +
						'<br/>Links: <br/>ETA in: ' +
						params.value[0] +
						' days<br/>' +
						params.value[4]
					);
				}
			},
			angleAxis: {
				type: 'value',
				startAngle: 0,
				boundaryGap: true,
				interval: 90,
				axisLabel: { show: false },
				splitLine: {
					show: true,
					lineStyle: {
						color: '#0f0f0f',
						width: 1
					}
				},
				axisLine: {
					show: false
				},
				axisTick: {
					show: false
				},
				alignTick: true
			},
			radiusAxis: {
				type: 'value',
				min: -10,
				max: 100,
				axisLabel: { show: true },
				axisLine: {
					show: false,
					symbol: ['arrow', 'none'],
					lineStyle: { width: 2 }
				},
				axisTick: {
					show: false
				}
			},
			series: [
				{
					name: '--',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data['--'],
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'To do',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.to_do,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'In progress',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.in_progress,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'On hold',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.on_hold,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Deprecated',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.deprecated,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Circle',
					type: 'line',
					coordinateSystem: 'polar',
					itemStyle: { borderJoin: 'round' },
					symbol: 'none',
					data: new Array(361).fill(0).map((_, index) => {
						return [30, index];
					}),
					lineStyle: {
						color: '#E73E51',
						width: 5
					},
					// If you don't want this to show up in the legend:
					showInLegend: false,
					silent: true,
					zlevel: -1
				},
				{
					name: 'Circle',
					type: 'line',
					coordinateSystem: 'polar',
					symbol: 'none',
					data: new Array(361).fill(0).map((_, index) => {
						return [60, index];
					}),
					lineStyle: {
						color: '#F8EA47',
						width: 5
					},
					// If you don't want this to show up in the legend:
					showInLegend: false,
					silent: true,
					zlevel: -1
				},
				{
					name: 'Circle',
					type: 'line',
					coordinateSystem: 'polar',
					symbol: 'none',
					data: new Array(361).fill(0).map((_, index) => {
						return [90, index];
					}),
					lineStyle: {
						color: '#00ADA8',
						width: 5
					},
					// If you don't want this to show up in the legend:
					showInLegend: false,
					silent: true,
					zlevel: -1
				}
			]
		};
		chart.on('click', function (params) {
			if (params.value && params.value[5]) {
				goto(`/applied-controls/${params.value[5]}`);
			}
		});

		chart.setOption(option);

		// Handle resize
		window.addEventListener('resize', function () {
			chart.resize();
			// Update the graphic elements positions after resize
			chart.setOption({
				graphic: getGraphicElements(chart)
			});
		});

		// Clean up event listener on component unmount
		return () => {
			window.removeEventListener('resize', function () {
				chart.resize();
				chart.setOption({
					graphic: getGraphicElements(chart)
				});
			});
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}" />
{#if data.not_displayed > 0}
	<a class="text-center hover:text-purple-600" href="/applied-controls?priority=null">
		⚠️ {data.not_displayed} items are not displayed as they don't have their priority set. Click here
		to review them.
	</a>
{/if}
