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
		maxValue?: number;
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
		compareName,
		maxValue = 100
	}: Props = $props();

	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(
			document.getElementById(chart_id),
			document.documentElement.classList.contains('dark') ? 'dark' : null,
			{ renderer: 'svg' }
		);

		// Prepare indicators with configurable max value and min -1 to avoid distortions with 0-values
		const indicators = labels.map((label) => ({
			name: label,
			min: -1,
			max: maxValue
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
					const suffix = maxValue === 100 ? '%' : '';
					return `${params.name}<br/>${dimensionName}: ${params.value[params.dataIndex]}${suffix}`;
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
								borderColor: document.documentElement.classList.contains('dark')
									? '#1e293b'
									: '#fff'
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
								borderColor: document.documentElement.classList.contains('dark')
									? '#1e293b'
									: '#fff'
							},
							label: {
								show: false
							}
						}
					]
				}
			]
		};

		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
