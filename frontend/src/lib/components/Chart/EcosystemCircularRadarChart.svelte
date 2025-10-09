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

		const maturityGroups = data.maturity_groups || ['<4', '4-5', '6-7', '>7'];
		const chartData = data[type] || {};
		// Use chart_max from backend to ensure consistent scale across current and residual
		const chartMax = data.chart_max || max;
		const categoryBoundaries = data.category_boundaries || [];
		const categoryLabelPositions = data.category_label_positions || [];

		// Define colors for maturity groups (matching original radar chart)
		const maturityColors = {
			'<4': '#E73E51', // red - low maturity
			'4-5': '#DE8898', // pink - medium-low maturity
			'6-7': '#BAD9EA', // light blue - medium-high maturity
			'>7': '#8A8B8A' // gray - high maturity
		};

		const option = {
			title: {
				text: title
			},
			graphic: [
				{
					type: 'text',
					left: 'center',
					top: 40,
					style: {
						text: m.cyberReliability(),
						font: 'bold 16px Arial',
						fill: '#333',
						textAlign: 'center'
					}
				}
			],
			legend: {
				data: maturityGroups,
				top: 60
			},
			grid: {
				top: 120,
				bottom: 60,
				left: 80,
				right: 80
			},
			polar: {
				center: ['50%', '55%'],
				radius: '65%'
			},
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
				startAngle: 0,
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
				axisLabel: { show: true },
				axisLine: {
					show: true,
					symbol: ['arrow', 'none'],
					lineStyle: { width: 2 }
				},
				axisTick: { show: false },
				splitLine: {
					show: true,
					lineStyle: {
						color: '#d1d5db',
						width: 1,
						type: 'solid'
					}
				},
				z: 0
			},
			series: [
				// Maturity group series
				...maturityGroups.map((group) => ({
					name: group,
					color: maturityColors[group],
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
					data: chartData[group] || [],
					animationDelay: function (idx) {
						return idx * 5;
					}
				})),
				// Category labels at outer ring
				{
					name: 'Category Labels',
					type: 'scatter',
					coordinateSystem: 'polar',
					symbolSize: 0,
					data: categoryLabelPositions.map((pos) => [0, pos.angle]),
					label: {
						show: true,
						position: 'outside',
						formatter: function (params) {
							const labelPos = categoryLabelPositions[params.dataIndex];
							return safeTranslate(labelPos.category);
						},
						fontSize: 14,
						fontWeight: 'bold',
						color: '#374151'
					},
					showInLegend: false,
					silent: true,
					z: 10
				},
				// Category delimiter lines
				...categoryBoundaries.map((angle) => ({
					name: 'Category Delimiter',
					type: 'line',
					coordinateSystem: 'polar',
					symbol: 'none',
					data: [
						[0, angle],
						[chartMax, angle]
					],
					lineStyle: {
						color: '#9ca3af',
						width: 2,
						type: 'dashed'
					},
					showInLegend: false,
					silent: true,
					z: 0
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
