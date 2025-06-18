<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	interface Props {
		name: string;
		s_label?: string;
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		orientation?: string;
		values: any[]; // Set the types for these variables later on
		colors?: string[];
	}

	let {
		name,
		s_label = '',
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		orientation = 'vertical',
		values = $bindable(),
		colors = []
	}: Props = $props();
	for (const index in values) {
		if (values[index].localName) {
			values[index].name = safeTranslate(values[index].localName);
		}
	}
	const chart_id = `${name}_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		const filteredValues = values.filter((item) => item.value > 0);
		// specify chart configuration item and data
		let option = {
			tooltip: {
				trigger: 'item',
				formatter: function (params) {
					// Return formatted tooltip content with just the name and value
					return `${params.data.name}: ${params.data.value}`;
				}
			},
			title: {
				text: title,
				textStyle: {
					fontWeight: 'bold',
					fontSize: 14
				}
				// show: false
			},
			toolbox: {
				show: true,
				feature: {
					mark: { show: true },
					dataView: { show: false, readOnly: true },
					saveAsImage: { show: false }
				}
			},
			legend: {
				top: 'bottom',
				right: '0',
				orient: orientation
			},
			series: [
				{
					name: s_label,
					type: 'pie',
					radius: ['40%', '70%'],
					avoidLabelOverlap: false,
					itemStyle: {
						borderRadius: 10,
						borderColor: '#fff',
						borderWidth: 2
					},
					label: {
						show: false,
						position: 'center'
					},
					emphasis: {
						label: {
							show: true,
							fontSize: 20,
							fontWeight: 'bold',
							formatter: function (params) {
								// Calculate the total value
								const total =
									params.data.value +
									values
										.filter((item) => item.name !== params.data.name)
										.reduce((sum, item) => sum + item.value, 0);

								// Calculate percentage
								const percent = ((params.data.value / total) * 100).toFixed(1);

								// Return formatted center label with just the name and percentage
								return `{name|${params.data.name}}\n{value|${percent}%}`;
							},
							rich: {
								name: {
									fontSize: 16,
									fontWeight: 'bold',
									lineHeight: 30
								},
								value: {
									fontSize: 14,
									lineHeight: 20
								}
							}
						}
					},
					labelLine: {
						show: false
					},
					data: filteredValues,
					color: colors
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

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
