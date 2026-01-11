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
		showPercentage?: boolean;
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
		colors = [],
		showPercentage = false
	}: Props = $props();
	for (const index in values) {
		if (values[index].localName) {
			values[index].name = safeTranslate(values[index].localName);
		} else {
			// Auto-translate common severity, detection, and status values
			const nameToTranslate = values[index].name?.toLowerCase();
			if (nameToTranslate) {
				const translatedName = safeTranslate(nameToTranslate);
				if (translatedName !== nameToTranslate) {
					values[index].name = translatedName;
				}
			}
		}
	}
	const chart_id = `${name}_div`;
	const formatDonutLabel = (params) => {
		const percent = params.percent?.toFixed(1) ?? '0.0';
		return `${percent}% (${params.value})`;
	};
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		const filteredValues = values.filter((item) => item.value > 0);
		// specify chart configuration item and data
		let option = {
			tooltip: {
				trigger: 'item',
				formatter: function (params) {
					// Only show the translated name in the tooltip on hover
					return params.data.name;
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
					radius: showPercentage ? ['30%', '55%'] : ['40%', '70%'],
					center: ['50%', '45%'],
					avoidLabelOverlap: true,
					itemStyle: {
						borderRadius: 10,
						borderColor: '#fff',
						borderWidth: 2
					},
					label: showPercentage
						? {
								show: true,
								position: 'outside',
								formatter: formatDonutLabel,
								fontSize: 16,
								fontWeight: 'bold',
								distanceToLabelLine: 2,
								overflow: 'break'
							}
						: {
								show: false,
								position: 'center'
							},
					emphasis: {
						scale: false,
						label: showPercentage
							? {
									show: true,
									formatter: formatDonutLabel,
									fontSize: 16,
									fontWeight: 'bold'
								}
							: { show: false }
					},
					labelLine: {
						show: showPercentage,
						length: 8,
						length2: 5
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
