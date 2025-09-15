<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		name: string;
		data?: Array<[string, number]>; // Array of [date, value] pairs
		year?: number;
		title?: string;
		width?: string;
		height?: string;
		classesContainer?: string;
		colorRange?: string[];
		onDateClick?: (date: string, value: number) => void;
	}

	let {
		name,
		data = [],
		year = new Date().getFullYear(),
		title = '',
		width = 'w-full',
		height = 'h-96',
		classesContainer = '',
		colorRange = ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
		onDateClick
	}: Props = $props();

	const chart_id = `${name}_calendar_div`;

	// Generate sample data if none provided
	function generateSampleData(year: number): Array<[string, number]> {
		const data: Array<[string, number]> = [];
		const startDate = new Date(year, 0, 1);
		const endDate = new Date(year, 11, 31);

		for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
			const dateStr = d.toISOString().split('T')[0];
			const value = Math.floor(Math.random() * 10); // Random value 0-9
			data.push([dateStr, value]);
		}

		return data;
	}

	onMount(async () => {
		const echarts = await import('echarts');
		let calendar_chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const chartData = data.length > 0 ? data : generateSampleData(year);
		const today = new Date().toISOString().split('T')[0];

		const option = {
			title: {
				text: title,
				textStyle: {
					fontWeight: 'bold',
					fontSize: 16
				},
				left: 'center',
				top: 10
			},
			tooltip: {
				formatter: function (params: any) {
					const date = new Date(params.value[0]);
					const value = params.value[1];
					return `${date.toLocaleDateString()}<br/>Activity: ${value}`;
				}
			},
			visualMap: {
				min: 0,
				max: 10,
				type: 'piecewise',
				orient: 'horizontal',
				left: 'center',
				top: title ? 50 : 20,
				pieces: [
					{ min: 0, max: 0, color: colorRange[0] },
					{ min: 1, max: 2, color: colorRange[1] },
					{ min: 3, max: 5, color: colorRange[2] },
					{ min: 6, max: 8, color: colorRange[3] },
					{ min: 9, max: 10, color: colorRange[4] }
				],
				show: false
			},
			calendar: {
				top: title ? 100 : 70,
				left: 30,
				right: 30,
				bottom: 20,
				cellSize: ['auto', 20],
				range: year,
				itemStyle: {
					borderWidth: 0.5,
					borderColor: '#fff'
				},
				yearLabel: { show: false },
				monthLabel: {
					nameMap: 'en',
					fontSize: 12
				},
				dayLabel: {
					fontSize: 10,
					nameMap: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
					firstDay: 1
				}
			},
			series: [
				{
					type: 'heatmap',
					coordinateSystem: 'calendar',
					data: chartData
				},
				{
					type: 'effectScatter',
					coordinateSystem: 'calendar',
					data: year === new Date().getFullYear() ? [[today, 0]] : [],
					symbolSize: function (val: any) {
						return 15;
					},
					itemStyle: {
						color: 'transparent',
						borderColor: '#1f2937',
						borderWidth: 2
					},
					zlevel: 1
				}
			]
		};

		calendar_chart.setOption(option);

		window.addEventListener('resize', function () {
			calendar_chart.resize();
		});

		// Add click event handler
		calendar_chart.on('click', function (params: any) {
			if (params.componentType === 'series') {
				let clickedDate: string;
				let clickedValue: number;

				if (params.seriesType === 'heatmap') {
					// Regular heatmap cell click
					clickedDate = params.value[0];
					clickedValue = params.value[1];
				} else if (params.seriesType === 'effectScatter') {
					// Current day marker click - find the corresponding value from chartData
					clickedDate = params.value[0];
					const dataPoint = chartData.find(([date]) => date === clickedDate);
					clickedValue = dataPoint ? dataPoint[1] : 0;
				} else {
					return;
				}

				if (onDateClick) {
					onDateClick(clickedDate, clickedValue);
				}
			}
		});
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
