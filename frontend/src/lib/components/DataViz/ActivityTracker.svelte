<script lang="ts">
	import { onMount } from 'svelte';
	interface Props {
		classesContainer?: string;
		name?: string;
		metrics: any;
	}

	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	let { classesContainer = '', name = 'metrics_tracker', metrics }: Props = $props();
	const chart_id = `${name}_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// Dynamically create gauge data from metrics progress
		const gaugeData = [];
		const progressEntries = Object.entries(metrics.progress);

		// Positioning calculations based on number of entries
		const entryCount = progressEntries.length;
		const spacingFactor = 60 / entryCount; // Adjust spacing based on number of metrics

		progressEntries.forEach(([key, value], index) => {
			// Calculate vertical position for each entry
			const centerPosition = -30 + index * spacingFactor;
			const titlePosition = centerPosition - 10;

			gaugeData.push({
				value: value,
				name: safeTranslate(key),
				title: {
					offsetCenter: ['0%', `${titlePosition}%`]
				},
				detail: {
					valueAnimation: true,
					offsetCenter: ['0%', `${centerPosition}%`]
				}
			});
		});

		// Generate colors dynamically based on number of entries
		const baseColors = ['#B075CC', '#91CC75', '#75BDCC', '#CC7575', '#CCBB75', '#75CC91'];
		const colors = baseColors.slice(0, entryCount);

		var option = {
			color: colors,
			series: [
				{
					type: 'gauge',
					radius: '100%',
					center: ['50%', '50%'],
					startAngle: 90,
					endAngle: -270,
					pointer: {
						show: false
					},
					tooltip: {
						show: true
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
							width: 66
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
						fontSize: 14,
						color: 'inherit',
						borderColor: 'inherit',
						borderRadius: 20,
						borderWidth: 1,
						formatter: '{value}%'
					}
				}
			]
		};

		// use configuration item and data specified to show chart
		chart.setOption(option);
		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

<div id={chart_id} class={classesContainer} style="width: 400px; height: 400px;"></div>
