<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { symbol } from 'zod';
	import { grid } from '@unovis/ts/components/axis/style';

	// export let name: string;

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = 'border';
	export let title = '';
	export let name = '';
	export let data;

	// data format: f1-f4 (fiabilité cyber = maturité x confiance ) to get the clusters and colors
	// x,y, z
	// x: criticité calculée avec cap à 5,5
	// y: the angle (output of dict to make sure they end up on the right quadrant, min: 45, max:-45) -> done on BE
	// z: the size of item (exposition = dependence x penetration) based on a dict, -> done on BE
	// label: name of the 3rd party entity
	//

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		const getGraphicElements = (chart) => {
			const chartWidth = chart.getWidth();
			const chartHeight = chart.getHeight();
			const centerX = chartWidth / 2;
			const centerY = chartHeight / 2;

			return [
				// Existing text elements
				{
					type: 'text',
					position: [chartWidth / 4, (3 * chartHeight) / 4],
					silent: true,
					style: {
						text: 'P3',
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
						text: 'P2',
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
						text: 'P1',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				}
			];
		};
		const mainAngles = [45, 135, 225, 315];
		const option = {
			title: {},
			graphic: getGraphicElements(chart),
			legend: {
				data: ['--', 'Govern', 'Identify', 'Protect', 'Detect', 'Respond', 'Recover'],
				top: 60
			},
			polar: {},
			tooltip: {
				formatter: function (params) {
					return params.value[3] + '<br/>Criticality: ' + params.value[0];
				}
			},
			angleAxis: {
				type: 'value',
				startAngle: 315,
				boundaryGap: true,
				interval: 45,
				axisLabel: { show: false },
				splitLine: {
					show: false
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
				max: 100,
				axisLabel: { show: false },
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
					color: '#F0F0F0',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.unclassified,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Govern',
					color: '#F9F49D',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.govern,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Identify',
					color: '#4CB2E0',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.identify,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Protect',
					color: '#9292EA',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.protect,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Detect',
					color: '#FAB746',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.protect,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Respond',
					color: '#F97367',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.protect,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: 'Recover',
					color: '#7DF49F',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.protect,
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
					name: 'MinorSplitLines',
					type: 'line',
					coordinateSystem: 'polar',
					symbol: 'none',
					silent: true,
					lineStyle: {
						color: '#1C263B',
						width: 1
					},
					data: mainAngles.flatMap((angle) => [
						[0, angle],
						[100, angle],
						[NaN, NaN]
					])
				}
			]
		};

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
