<script lang="ts">
	import { onMount } from 'svelte';

	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';
	import { m } from '$paraglide/messages';

	interface Props {
		points?: any[];
		width?: string;
		height?: string;
		classesContainer?: string;
		name?: string;
	}

	let {
		points = [],
		width = 'w-full',
		height = 'h-72',
		classesContainer = '',
		name = 'posture_trend'
	}: Props = $props();

	const chart_id = `${name}_div`;

	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			if (!active) return;
			const el = document.getElementById(chart_id);
			if (!el) return;
			let chart: any;
			const disposeChart = mountThemeAwareChart(
				echarts,
				el,
				() => {
					const data = points
						.filter((p) => p.score != null)
						.map((p) => ({ value: [p.timestamp, p.score], counts: p.counts }));

					const times = data.map((d) => new Date(d.value[0]).getTime());
					const spanMs = times.length > 1 ? Math.max(...times) - Math.min(...times) : 0;
					const dayMs = 24 * 3600 * 1000;
					const axisLabelFormatter = (value: number) => {
						const date = new Date(value);
						if (spanMs <= dayMs)
							return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
						if (spanMs <= 7 * dayMs)
							return date.toLocaleString([], {
								month: 'short',
								day: 'numeric',
								hour: '2-digit',
								minute: '2-digit'
							});
						return date.toLocaleDateString();
					};

					const option = {
						backgroundColor: 'transparent',
						grid: { top: 20, right: 30, bottom: 40, left: 50 },
						tooltip: {
							trigger: 'axis',
							formatter: (params: any) => {
								const p = params[0];
								const counts = p.data.counts ?? {};
								const detail = ['pass', 'fail', 'error', 'not_applicable', 'not_checked']
									.filter((k) => counts[k])
									.map((k) => `${k}: ${counts[k]}`)
									.join(', ');
								return `${new Date(p.value[0]).toLocaleString()}<br/>${p.marker}${m.passRate()}: ${p.value[1]}%${detail ? `<br/>${detail}` : ''}`;
							}
						},
						xAxis: {
							type: 'time',
							axisLabel: { formatter: axisLabelFormatter, hideOverlap: true }
						},
						yAxis: {
							type: 'value',
							min: 0,
							max: 100,
							axisLabel: { formatter: '{value}%' },
							splitLine: { show: true }
						},
						series: [
							{
								name: m.passRate(),
								type: 'line',
								sampling: 'lttb',
								smooth: true,
								symbol: 'circle',
								symbolSize: 7,
								areaStyle: {
									opacity: 0.6,
									color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
										{ offset: 0, color: 'rgba(134, 239, 172, 0.8)' },
										{ offset: 1, color: 'rgba(134, 239, 172, 0.05)' }
									])
								},
								lineStyle: { color: '#22c55e' },
								itemStyle: { color: '#22c55e' },
								data
							}
						]
					};
					return option;
				},
				{ onChart: (c) => (chart = c) }
			);
			// the helper only watches window resize; this also catches container-only changes
			const observer = new ResizeObserver(() => chart?.resize());
			observer.observe(el);
			dispose = () => {
				observer.disconnect();
				disposeChart();
			};
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
