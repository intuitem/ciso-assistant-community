<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import * as m from '$paraglide/messages.js';

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
					left: 'center',
					top: 40,
					style: {
						text: m.cyberReliability(),
						font: 'bold 16px Arial',
						fill: '#333',
						textAlign: 'center'
					}
				},
				{
					type: 'text',
					position: [chartWidth / 4, (3 * chartHeight) / 4],
					silent: true,
					style: {
						text: m.suppliers(),
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
						text: m.partners(),
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
						text: m.clients(),
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
			title: {
				text: title
			},
			graphic: getGraphicElements(chart),
			legend: {
				data: ['<4', '4-5', '6-7', '>7'],
				top: 60
			},
			polar: {},
			tooltip: {
				formatter: function (params) {
					return (
						params.value[3].split('-')[0] +
						' - ' +
						safeTranslate(params.value[3].split('-')[1]) +
						`<br/>${m.criticalitySemiColon()} ` +
						params.value[0]
					);
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
				max: 6,
				inverse: true,
				axisLabel: { show: true },
				axisLine: {
					show: true,
					symbol: ['arrow', 'none'],
					lineStyle: { width: 2 }
				},
				axisTick: {
					show: false
				}
			},
			series: [
				{
					name: '<4',
					color: '#E73E51',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.clst1,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: '4-5',
					color: '#DE8898',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.clst2,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: '6-7',
					color: '#BAD9EA',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.clst3,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: '>7',
					color: '#8A8B8A',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.clst4,
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
					data: new Array(360).fill(0).map((_, index) => {
						return [2.5, index];
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
					data: new Array(360).fill(0).map((_, index) => {
						return [0.2, index];
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
					data: new Array(360).fill(0).map((_, index) => {
						return [0.9, index];
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
				// Center blue dot
				{
					name: 'CenterDot',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbol: 'circle',
					symbolSize: 30,
					itemStyle: {
						color: '#007FB9',
						borderWidth: 1
					},
					data: [[5.999, 0]],
					silent: true,
					zlevel: -1,
					showInLegend: false
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
						[6, angle],
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
	<div class="text-center">
		⚠️ {data.not_displayed} items are not displayed as they are lacking data.
	</div>
{/if}
