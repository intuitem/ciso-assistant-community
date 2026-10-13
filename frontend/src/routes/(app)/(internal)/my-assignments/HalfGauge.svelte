<script lang="ts">
	import { onMount } from 'svelte';

	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';

	interface Props {
		classesContainer?: string;
		name: string;
		value?: number;
	}

	let { classesContainer = '', name, value = 0 }: Props = $props();
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
				// specify chart configuration item and data

				const gaugeData = [
					{
						value: value,
						detail: {
							valueAnimation: true,
							offsetCenter: ['0%', '0%']
						}
					}
				];
				var option = {
					series: [
						{
							type: 'gauge',
							radius: '120%',
							center: ['50%', '70%'],
							startAngle: 180,
							endAngle: 360,
							pointer: {
								show: false
							},
							progress: {
								show: true,
								overlap: false,
								roundCap: true,
								clip: false,
								itemStyle: {
									borderWidth: 1,
									borderColor: '#464646'
								}
							},
							axisLine: {
								lineStyle: {
									width: 20
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
							data: gaugeData,
							detail: {
								width: 40,
								height: 14,
								fontSize: 16,
								color: 'inherit',
								borderColor: 'inherit',
								borderRadius: 20,
								borderWidth: 1,
								formatter: '{value}%'
							}
						}
					]
				};
				// console.debug(option);

				// use configuration item and data specified to show chart
				return option;
			});
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class=" {classesContainer} " style="width: 300px; height: 200px;"></div>
