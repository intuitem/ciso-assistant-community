<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { show } from '$paraglide/messages/pt';
	import { axis } from '@unovis/ts/components/axis/style';

	// export let name: string;
	export let s_label = '';

	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let title = '';
	export let name = '';

	export let values: any[]; // Set the types for these variables later on
	export let labels: any[];

	const axisVal = 16;

	for (const index in values) {
		if (values[index].localName) {
			values[index].name = safeTranslate(values[index].localName);
		}
	}

	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// specify chart configuration item and data
		// prettier-ignore
		//14 segments
		const data = {
      "s1": [
        [5, 45, 5],
        [4, 45, 10]
      ],
      "s2": [
			[1, 180, 15],
			[1, 180 + 45, 10]
      ],
      "s3": [
			[2, 270, 5],
			[1, 180 + 90, 12]
      ],
      "s4": [
			[1, 300, 6],
			[1, 315, 20]
      ],
    };
		const option = {
			title: {
				text: 'Ecosystem'
			},
			graphic: [
				{
					type: 'text',
					position: [chart.getWidth() / 4, (3 * chart.getHeight()) / 4],
					rotation: 0,
					origin: [chart.getWidth() / 2, chart.getWidth() / 2],
					style: {
						text: 'Prestataires',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				},
				{
					type: 'text',
					position: [(3 * chart.getWidth()) / 4, chart.getHeight() / 4],
					rotation: 0,
					origin: [chart.getWidth() / 2, chart.getWidth() / 2],
					style: {
						text: 'Partenaires',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				},
				{
					type: 'text',
					position: [chart.getWidth() / 4, chart.getHeight() / 4],
					rotation: 0,
					origin: [chart.getWidth() / 2, chart.getWidth() / 2],
					style: {
						text: 'Clients',
						font: '18px Arial',
						fill: '#666',
						textAlign: 'center',
						textVerticalAlign: 'middle'
					}
				}
			],
			legend: {
				data: ['<4', '4-5', '6-7', '>7'],
				left: 'right'
			},
			polar: {},
			tooltip: {
				formatter: function (params) {
					return params.value[2] + ' commits in ';
				}
			},
			angleAxis: {
				type: 'value',
				startAngle: 315,
				boundaryGap: true,
				interval: 45,
				axisLabel: { show: false },
				splitLine: {
					show: true
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
					show: false
				},
				axisTick: {
					show: false
				}
			},
			series: [
				{
					name: '<4',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.s1,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: '4-5',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.s2,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: '6-7',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.s3,
					animationDelay: function (idx) {
						return idx * 5;
					}
				},
				{
					name: '>7',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						return val[2] * 2;
					},
					data: data.s4,
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
						width: 4
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
						width: 4
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
						width: 4
					},
					// If you don't want this to show up in the legend:
					showInLegend: false,
					silent: true,
					zlevel: -1
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

<div id={chart_id} class="{width} {height} {classesContainer}" />
