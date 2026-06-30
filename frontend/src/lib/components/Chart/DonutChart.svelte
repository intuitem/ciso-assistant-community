<script lang="ts">
	import { onMount } from 'svelte';
	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';
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
		showLegend?: boolean;
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
		showPercentage = false,
		showLegend = true
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
	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			if (!active) return;
			const el = document.getElementById(chart_id);
			if (!el) return;
			dispose = mountThemeAwareChart(echarts, el, () => {
				const filteredEntries = values
					.map((item, i) => ({ item, color: colors[i] }))
					.filter((entry) => entry.item.value > 0);
				const filteredValues = filteredEntries.map((entry) => entry.item);
				const filteredColors = filteredEntries.map((entry) => entry.color);
				return {
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
					},
					toolbox: {
						show: true,
						feature: {
							mark: { show: true },
							dataView: { show: false, readOnly: true },
							saveAsImage: { show: false }
						}
					},
					legend: showLegend
						? {
								top: 'bottom',
								right: '0',
								orient: orientation
							}
						: { show: false },
					series: [
						{
							name: s_label,
							type: 'pie',
							radius: showPercentage ? ['30%', '55%'] : ['40%', '70%'],
							center: showLegend ? ['50%', '45%'] : ['50%', '50%'],
							avoidLabelOverlap: true,
							itemStyle: {
								borderRadius: 10,
								borderColor: document.documentElement.classList.contains('dark')
									? '#1e293b'
									: '#fff',
								borderWidth: 2
							},
							label: showPercentage
								? {
										show: true,
										position: 'outside',
										formatter: '{d}%',
										fontSize: 10,
										fontWeight: 'bold',
										distanceToLabelLine: 2
									}
								: {
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
											filteredValues
												.filter((item) => item.name !== params.data.name)
												.reduce((sum, item) => sum + item.value, 0);

										// Calculate percentage
										const percent = ((params.data.value / total) * 100).toFixed(1);

										// Return formatted center label with just the name and percentage
										return `{value|${percent}%}`;
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
								show: showPercentage,
								length: 8,
								length2: 5
							},
							data: filteredValues,
							color: filteredColors
						}
					]
				};
			});
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
