<script lang="ts">
	import { onMount } from 'svelte';
	import { mountThemeAwareChart, isDarkTheme } from '$lib/utils/echartsTheme';
	import { m } from '$paraglide/messages';

	interface Couple {
		id: string;
		risk_origin: string;
		target_objective: string;
		target_objective_category: string;
		pertinence_level: number;
		is_selected: boolean;
	}

	interface Props {
		couples: Couple[];
		// Pertinence labels, lowest level first (the study matrix's scale)
		pertinenceLabels: string[];
		// Fiche méthode 4 draws two views: sectors by risk origin or by target objective category
		groupBy: 'origin' | 'objective';
		title: string;
		name: string;
		height?: string;
	}

	let { couples, pertinenceLabels, groupBy, title, name, height = 'h-[560px]' }: Props = $props();

	// Fiche méthode 4 colour code
	const RETAINED = '#e53935';
	const NOT_RETAINED = '#43a047';

	const chartId = `${name}_radar_div`;

	function truncate(text: string, size = 28): string {
		return text.length > size ? `${text.slice(0, size - 1)}…` : text;
	}

	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			const el = document.getElementById(chartId);
			if (!active || !el) return;

			const levels = pertinenceLabels.length;
			const outer = levels + 0.5;
			const sectorOf = (c: Couple) =>
				groupBy === 'origin' ? c.risk_origin : c.target_objective_category;
			const labelOf = (c: Couple) =>
				groupBy === 'origin' ? truncate(c.target_objective) : c.risk_origin;
			const sectors = [...new Set(couples.map(sectorOf))].sort((a, b) => a.localeCompare(b));
			const span = sectors.length ? 360 / sectors.length : 360;
			// Most relevant couples sit at the centre (fiche méthode 4); unrated ones on the rim.
			const points = sectors.flatMap((sector, index) => {
				const inSector = couples.filter((c) => sectorOf(c) === sector);
				return inSector.map((couple, rank) => ({
					value: [
						couple.pertinence_level > 0 ? couple.pertinence_level : 0.25,
						index * span + (span * (rank + 1)) / (inSector.length + 1)
					],
					couple,
					itemStyle: { color: couple.is_selected ? RETAINED : NOT_RETAINED }
				}));
			});

			let chart: any;
			// The chart mounts while its accordion is still opening: follow the container size.
			const observer = new ResizeObserver(() => chart?.resize());
			observer.observe(el);
			const unmount = mountThemeAwareChart(
				echarts,
				el,
				() => {
					const isDark = isDarkTheme();
					const labelColor = isDark ? '#cbd5e1' : '#475569';
					const gridColor = isDark ? '#475569' : '#d1d5db';
					return {
						title: {
							text: title,
							left: 'center',
							textStyle: { fontSize: 14, color: labelColor }
						},
						polar: { center: ['50%', '54%'], radius: '72%' },
						angleAxis: {
							type: 'value',
							min: 0,
							max: 360,
							startAngle: 90,
							clockwise: true,
							axisLabel: { show: false },
							axisTick: { show: false },
							axisLine: { show: false },
							splitLine: { show: false }
						},
						radiusAxis: {
							type: 'value',
							min: 0,
							max: outer,
							inverse: true,
							interval: 1,
							axisLine: { show: false },
							axisTick: { show: false },
							axisLabel: {
								color: labelColor,
								fontSize: 10,
								formatter: (value: number) =>
									value >= 1 && value <= levels ? `${value} · ${pertinenceLabels[value - 1]}` : ''
							},
							splitLine: { show: true, lineStyle: { color: gridColor } },
							z: 10
						},
						tooltip: {
							formatter: (params: any) => {
								const couple: Couple | undefined = params.data?.couple;
								if (!couple) return '';
								const level = couple.pertinence_level;
								return [
									`<b>${couple.risk_origin}</b>`,
									couple.target_objective,
									couple.target_objective_category,
									`${m.pertinence()} : ${level > 0 ? `${level} · ${pertinenceLabels[level - 1]}` : '--'}`,
									couple.is_selected ? m.selected() : m.notSelected()
								].join('<br/>');
							}
						},
						series: [
							{
								type: 'scatter',
								coordinateSystem: 'polar',
								symbolSize: 16,
								data: points,
								label: {
									show: true,
									position: 'right',
									color: labelColor,
									fontSize: 10,
									formatter: (params: any) => labelOf(params.data.couple)
								},
								labelLayout: { hideOverlap: true }
							},
							{
								type: 'line',
								coordinateSystem: 'polar',
								silent: true,
								symbol: 'none',
								lineStyle: { color: gridColor, type: 'dashed' },
								data: sectors.flatMap((_, index) => [
									[outer, index * span],
									[0, index * span],
									[null, null]
								]),
								connectNulls: false
							},
							{
								type: 'scatter',
								coordinateSystem: 'polar',
								silent: true,
								symbolSize: 0,
								data: sectors.map((sector, index) => ({
									value: [0, index * span + span / 2],
									name: sector
								})),
								label: {
									show: true,
									position: 'outside',
									color: labelColor,
									fontSize: 12,
									fontWeight: 'bold',
									formatter: (params: any) => params.name
								}
							}
						]
					};
				},
				{ onChart: (instance: any) => (chart = instance) }
			);
			dispose = () => {
				observer.disconnect();
				unmount();
			};
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chartId} class="w-full {height}"></div>
