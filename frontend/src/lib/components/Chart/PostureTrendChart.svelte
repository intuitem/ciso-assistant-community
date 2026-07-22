<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
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
	let cleanup: (() => void) | undefined;

	onMount(async () => {
		const echarts = await import('echarts');
		const chart = echarts.init(
			document.getElementById(chart_id),
			document.documentElement.classList.contains('dark') ? 'dark' : null,
			{ renderer: 'svg' }
		);

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

		chart.setOption(option);
		const container = document.getElementById(chart_id);
		const observer = new ResizeObserver(() => chart.resize());
		if (container) observer.observe(container);
		const onWindowResize = () => chart.resize();
		window.addEventListener('resize', onWindowResize);
		cleanup = () => {
			observer.disconnect();
			window.removeEventListener('resize', onWindowResize);
			chart.dispose();
		};
	});

	onDestroy(() => cleanup?.());
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
