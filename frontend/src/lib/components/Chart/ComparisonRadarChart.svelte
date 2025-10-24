<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name?: string;
		labels: string[];
		baseData: number[];
		compareData: number[];
		baseName: string;
		compareName: string;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name = '',
		labels,
		baseData,
		compareData,
		baseName,
		compareName
	}: Props = $props();

	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// Debug: Log the data
		console.log('Radar Chart Data:', {
			name,
			labels,
			baseData,
			compareData,
			baseName,
			compareName
		});

		// Prepare indicators with max value of 100 (percentage)
		const indicators = labels.map((label) => ({
			name: label,
			max: 100
		}));

		const option = {
			title: {
				text: title,
				textStyle: {
					fontWeight: 'bold',
					fontSize: 16
				}
			},
			tooltip: {
				trigger: 'item',
				formatter: function (params: any) {
					const dimensionName = indicators[params.dataIndex]?.name || '';
					return `${params.name}<br/>${dimensionName}: ${params.value[params.dataIndex]}%`;
				}
			},
			legend: {
				data: [baseName, compareName],
				bottom: 10,
				type: 'scroll'
			},
			radar: {
				shape: 'polygon',
				indicator: indicators,
				radius: '60%',
				center: ['50%', '50%'],
				splitNumber: 5,
				axisName: {
					color: '#666',
					fontSize: 11,
					overflow: 'truncate',
					width: 80
				},
				splitLine: {
					lineStyle: {
						color: '#ddd'
					}
				},
				splitArea: {
					show: true,
					areaStyle: {
						color: ['rgba(255, 255, 255, 0)', 'rgba(220, 220, 220, 0.1)']
					}
				},
				axisLine: {
					lineStyle: {
						color: '#999'
					}
				}
			},
			series: [
				{
					name: 'Audit Comparison',
					type: 'radar',
					emphasis: {
						lineStyle: {
							width: 4
						}
					},
					data: [
						{
							value: baseData,
							name: baseName,
							symbol: 'circle',
							symbolSize: 8,
							lineStyle: {
								color: '#3b82f6',
								width: 3,
								type: 'solid'
							},
							areaStyle: {
								color: 'rgba(59, 130, 246, 0.15)'
							},
							itemStyle: {
								color: '#3b82f6',
								borderWidth: 2,
								borderColor: '#fff'
							},
							label: {
								show: false
							}
						},
						{
							value: compareData,
							name: compareName,
							symbol: 'diamond',
							symbolSize: 10,
							lineStyle: {
								color: '#f97316',
								width: 3,
								type: 'dashed',
								dashOffset: 5
							},
							areaStyle: {
								color: 'rgba(249, 115, 22, 0.15)'
							},
							itemStyle: {
								color: '#f97316',
								borderWidth: 2,
								borderColor: '#fff'
							},
							label: {
								show: false
							}
						}
					]
				}
			]
		};

		console.log('ECharts Option:', JSON.stringify(option, null, 2));
		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
