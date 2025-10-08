<script lang="ts">
	import { onMount } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name?: string;
		data: any;
		type: 'current' | 'residual';
		max?: any;
		greenZoneRadius?: any;
		yellowZoneRadius?: any;
		redZoneRadius?: any;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = 'border',
		title = '',
		name = '',
		data,
		type,
		max = page.data.settings.ebios_radar_max,
		greenZoneRadius = page.data.settings.ebios_radar_green_zone_radius,
		yellowZoneRadius = page.data.settings.ebios_radar_yellow_zone_radius,
		redZoneRadius = page.data.settings.ebios_radar_red_zone_radius
	}: Props = $props();

	const chart_id = `${name}_circular_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		const categories = data.categories || [];
		const chartData = data[type] || {};
		const chartMax = data.chart_max || max;

		// Define colors for categories
		const categoryColors = [
			'#3b82f6', // blue
			'#ef4444', // red
			'#10b981', // green
			'#f59e0b', // amber
			'#8b5cf6', // purple
			'#ec4899', // pink
			'#14b8a6', // teal
			'#f97316'  // orange
		];

		const option = {
			title: {
				text: title
			},
			legend: {
				data: categories.map((cat) => safeTranslate(cat)),
				top: 60
			},
			polar: {},
			tooltip: {
				formatter: function (params) {
					const parts = params.value[3].split('-');
					return (
						parts[0] +
						' - ' +
						safeTranslate(parts[1] || '') +
						`<br/>${m.criticalitySemiColon()} ` +
						params.value[0]
					);
				}
			},
			angleAxis: {
				type: 'value',
				startAngle: 90,
				min: 0,
				max: 360,
				axisLabel: { show: false },
				splitLine: { show: false },
				axisLine: { show: false },
				axisTick: { show: false }
			},
			radiusAxis: {
				type: 'value',
				max: chartMax,
				inverse: true,
				axisLabel: { show: false },
				axisLine: { show: false },
				axisTick: { show: false },
				splitLine: {
					show: true,
					lineStyle: {
						color: '#d1d5db',
						width: 1,
						type: 'solid'
					}
				}
			},
			series: [
				// Category series
				...categories.map((category, index) => ({
					name: safeTranslate(category),
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: function (val) {
						// val[2] contains the exposure value (dependency * penetration * 4), range 0-64
						// Scale with offset to ensure visibility
						const exposure = val[2];
						const baseSize = 12; // Base size for zero exposure
						const additionalSize = 20; // Additional size range based on exposure
						const maxExposure = 64; // 4 * 4 * 4
						return baseSize + (exposure / maxExposure) * additionalSize;
					},
					data: chartData[category] || [],
					animationDelay: function (idx) {
						return idx * 5;
					}
				})),
				// Threshold circles
				{
					name: 'Red Zone',
					type: 'line',
					coordinateSystem: 'polar',
					symbol: 'none',
					data: Array.from({ length: 361 }, (_, i) => [redZoneRadius, i]),
					lineStyle: {
						color: '#E73E51',
						width: 5
					},
					showInLegend: false,
					silent: true,
					z: 1
				},
				{
					name: 'Yellow Zone',
					type: 'line',
					coordinateSystem: 'polar',
					symbol: 'none',
					data: Array.from({ length: 361 }, (_, i) => [yellowZoneRadius, i]),
					lineStyle: {
						color: '#F8EA47',
						width: 5
					},
					showInLegend: false,
					silent: true,
					z: 1
				},
				{
					name: 'Green Zone',
					type: 'line',
					coordinateSystem: 'polar',
					symbol: 'none',
					data: Array.from({ length: 361 }, (_, i) => [greenZoneRadius, i]),
					lineStyle: {
						color: '#00ADA8',
						width: 5
					},
					showInLegend: false,
					silent: true,
					z: 1
				}
			]
		};

		chart.setOption(option);

		// Handle resize
		const resizeHandler = function () {
			chart.resize();
		};

		window.addEventListener('resize', resizeHandler);

		// Clean up event listener on component unmount
		return () => {
			window.removeEventListener('resize', resizeHandler);
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
{#if data.not_displayed > 0}
	<div class="text-center">
		⚠️ {data.not_displayed} items are not displayed as they are lacking data.
	</div>
{/if}
