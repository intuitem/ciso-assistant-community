<script lang="ts">
	import { onMount } from 'svelte';

	import { isDarkTheme, mountThemeAwareChart } from '$lib/utils/echartsTheme';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
		value: number;
		max: number;
		min?: number;
		isPercentage?: boolean;
		color?: string;
		backgroundColor?: string;
		strokeWidth?: number;
		fontSize?: number;
		title?: string;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		name = 'single_gauge',
		value,
		max,
		min = 0,
		isPercentage = false,
		color = '#B075CC',
		backgroundColor,
		strokeWidth = 20,
		fontSize = 32,
		title = ''
	}: Props = $props();

	const chart_id = `${name}_${crypto.randomUUID().slice(0, 8)}_div`;

	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			if (!active) return;
			const el = document.getElementById(chart_id);
			if (!el) return;

			// Capture values at mount time to avoid reactive context issues in ECharts callbacks
			const range = max - min;
			const percentage = range > 0 ? ((value - min) / range) * 100 : 0;
			const displayValue = Math.round(value * 10) / 10;

			dispose = mountThemeAwareChart(echarts, el, () => {
				// Recomputed on every theme flip so the value and track stay readable on both surfaces.
				const isDark = isDarkTheme();
				const valueColor = isDark ? '#e5e5e5' : '#333';
				const trackColor = backgroundColor ?? (isDark ? '#475569' : '#E6E6E6');
				return {
					title: {
						text: title,
						textStyle: {
							fontWeight: 'bold',
							fontSize: 14,
							color: valueColor
						}
					},
					series: [
						{
							type: 'gauge',
							radius: '65%',
							center: ['50%', '45%'],
							startAngle: 90,
							endAngle: -270,
							min: 0,
							max: 100,
							pointer: {
								show: false
							},
							progress: {
								show: true,
								width: strokeWidth,
								roundCap: true,
								itemStyle: {
									color: color
								}
							},
							axisLine: {
								lineStyle: {
									width: strokeWidth,
									color: [[1, trackColor]]
								}
							},
							splitLine: {
								show: false
							},
							axisTick: {
								show: false
							},
							axisLabel: {
								show: false
							},
							title: {
								show: false
							},
							data: [
								{
									value: percentage,
									detail: {
										valueAnimation: true,
										offsetCenter: ['0%', '0%'],
										fontSize: fontSize,
										fontWeight: 'bold',
										color: valueColor,
										formatter: function () {
											return isPercentage ? `${displayValue}%` : displayValue;
										}
									}
								}
							],
							detail: {
								width: 80,
								height: 60,
								fontSize: fontSize,
								fontWeight: 'bold',
								color: valueColor,
								backgroundColor: 'transparent',
								borderWidth: 0
							}
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

<div
	id={chart_id}
	class="{width} {height} {classesContainer}"
	style="min-width: 180px; min-height: 180px;"
	data-testid="progress-ring-svg"
	aria-valuenow={value}
	aria-valuemin={min}
	aria-valuemax={max}
	role="progressbar"
></div>
