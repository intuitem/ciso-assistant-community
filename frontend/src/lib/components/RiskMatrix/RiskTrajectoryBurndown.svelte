<script lang="ts">
	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';
	import { safeTranslate } from '$lib/utils/i18n';
	import { isoDay, type BurndownPoint } from './trajectory';

	interface Props {
		points: BurndownPoint[];
		levels: { name: string; hexcolor?: string }[];
		start: string;
		end: string;
		cursor: string;
		onpick?: (date: string) => void;
	}

	let { points, levels, start, end, cursor, onpick }: Props = $props();

	let chart: any;

	function cursorLine(date: string) {
		return {
			silent: true,
			symbol: 'none',
			label: { show: false },
			lineStyle: { color: '#475569', type: 'dashed', width: 1.5 },
			data: [{ xAxis: date }]
		};
	}

	function buildOption() {
		const order = levels.map((_, i) => i).reverse();
		const series = order.map((levelIndex, i) => ({
			id: `level-${levelIndex}`,
			name: safeTranslate(levels[levelIndex].name),
			type: 'line',
			stack: 'levels',
			step: 'end',
			showSymbol: false,
			lineStyle: { width: 1 },
			areaStyle: { opacity: 0.75 },
			itemStyle: { color: levels[levelIndex].hexcolor ?? '#94a3b8' },
			data: [
				...points.map((p) => [p.date, p.counts[levelIndex]]),
				[end, points.at(-1)?.counts[levelIndex] ?? 0]
			],
			...(i === 0 ? { markLine: cursorLine(cursor) } : {})
		}));
		return {
			tooltip: { trigger: 'axis' },
			legend: { top: 0, textStyle: { fontSize: 11 } },
			grid: { left: 36, right: 16, top: 32, bottom: 24 },
			xAxis: { type: 'time', min: start, max: end, axisLabel: { fontSize: 10 } },
			yAxis: { type: 'value', minInterval: 1, axisLabel: { fontSize: 10 } },
			series
		};
	}

	function mount(el: HTMLElement) {
		let dispose: (() => void) | undefined;
		let active = true;
		import('echarts').then((echarts) => {
			if (!active || !el.isConnected) return;
			dispose = mountThemeAwareChart(echarts, el, buildOption, {
				onChart: (instance: any) => {
					chart = instance;
					chart.getZr().on('click', (event: any) => {
						const [x] = chart.convertFromPixel({ gridIndex: 0 }, [event.offsetX, event.offsetY]);
						if (Number.isFinite(x)) onpick?.(isoDay(new Date(x)));
					});
				}
			});
		});
		return {
			destroy() {
				active = false;
				dispose?.();
			}
		};
	}

	$effect(() => {
		const date = cursor;
		const topLevel = levels.length - 1;
		chart?.setOption({ series: [{ id: `level-${topLevel}`, markLine: cursorLine(date) }] });
	});
</script>

<div class="w-full h-56" use:mount data-testid="trajectory-burndown"></div>
