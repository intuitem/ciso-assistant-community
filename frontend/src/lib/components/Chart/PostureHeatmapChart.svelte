<script lang="ts">
	import { onMount } from 'svelte';

	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';
	import { m } from '$paraglide/messages';

	interface Props {
		results?: any[];
		assets?: { id: string; name: string }[];
		width?: string;
		classesContainer?: string;
		name?: string;
		onCellClick?: (row: any) => void;
	}

	let {
		results = [],
		assets = [],
		width = 'w-full',
		classesContainer = '',
		name = 'posture_heatmap',
		onCellClick
	}: Props = $props();

	const chart_id = `${name}_div`;

	const RESULT_ORDER = ['fail', 'error', 'not_checked', 'not_applicable', 'pass'];
	const RESULT_COLORS = ['#f87171', '#fbbf24', '#d1d5db', '#6b7280', '#86efac'];
	const resultLabels: Record<string, string> = {
		pass: m.pass(),
		fail: m.fail(),
		not_applicable: m.notApplicable(),
		error: m.error(),
		not_checked: m.notChecked()
	};

	const checks = $derived.by(() => {
		const seen = new Map();
		for (const row of results) seen.set(row.requirement.id, row.requirement);
		return [...seen.values()].sort((a, b) =>
			(b.ref_id ?? '').localeCompare(a.ref_id ?? '', undefined, { numeric: true })
		);
	});

	const columns = $derived(
		[...assets].sort((a, b) =>
			(a.name ?? '').localeCompare(b.name ?? '', undefined, { numeric: true })
		)
	);

	const Y_WINDOW = 40;
	const X_WINDOW = 20;
	const chartHeight = $derived(Math.max(280, Math.min(checks.length, Y_WINDOW) * 24 + 160));

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
					const latestTimestamp = results.reduce(
						(acc, r) => (r.timestamp > acc ? r.timestamp : acc),
						''
					);
					const assetIndex = new Map(columns.map((a, i) => [a.id, i]));
					const checkIndex = new Map(checks.map((c, i) => [c.id, i]));

					const data = results
						.filter((r) => assetIndex.has(r.asset.id))
						.map((r) => ({
							value: [
								assetIndex.get(r.asset.id),
								checkIndex.get(r.requirement.id),
								RESULT_ORDER.indexOf(r.result)
							],
							row: r,
							itemStyle: r.timestamp < latestTimestamp ? { opacity: 0.55 } : undefined
						}));

					const dataZoom = [
						...(columns.length > X_WINDOW
							? [
									{
										type: 'slider',
										xAxisIndex: 0,
										bottom: 34,
										height: 16,
										startValue: 0,
										endValue: X_WINDOW - 1,
										zoomLock: false
									}
								]
							: []),
						...(checks.length > Y_WINDOW
							? [
									{
										type: 'slider',
										yAxisIndex: 0,
										right: 4,
										width: 16,
										startValue: checks.length - 1,
										endValue: checks.length - Y_WINDOW
									}
								]
							: [])
					];

					const option = {
						backgroundColor: 'transparent',
						grid: {
							top: 60,
							right: checks.length > Y_WINDOW ? 40 : 10,
							bottom: columns.length > X_WINDOW ? 90 : 60,
							left: 90
						},
						dataZoom,
						tooltip: {
							position: 'top',
							formatter: (params: any) => {
								const r = params.data.row;
								const parts = [
									`<b>${r.requirement.ref_id}</b> ${r.requirement.name ?? ''}`,
									`${params.marker}${resultLabels[r.result] ?? r.result} — ${r.asset.str}`,
									new Date(r.timestamp).toLocaleString()
								];
								if (r.actual) parts.push(`actual: ${r.actual}`);
								if (r.expected) parts.push(`expected: ${r.expected}`);
								if (r.message) parts.push(r.message);
								if (onCellClick) {
									parts.push(`<i style="opacity:0.65;font-size:11px">${m.heatmapCellHint()}</i>`);
								}
								return parts.join('<br/>');
							}
						},
						xAxis: {
							type: 'category',
							data: columns.map((a) => a.name),
							position: 'top',
							axisLabel: { rotate: columns.length > 6 ? 30 : 0 },
							splitArea: { show: true }
						},
						yAxis: {
							type: 'category',
							data: checks.map((c) => c.ref_id),
							axisLabel: { interval: 0 },
							splitArea: { show: true }
						},
						visualMap: {
							type: 'piecewise',
							orient: 'horizontal',
							bottom: 0,
							left: 'center',
							min: 0,
							max: RESULT_ORDER.length - 1,
							pieces: RESULT_ORDER.map((key, i) => ({
								value: i,
								label: resultLabels[key] ?? key,
								color: RESULT_COLORS[i]
							}))
						},
						series: [
							{
								type: 'heatmap',
								data,
								label: { show: false },
								emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0, 0, 0, 0.4)' } }
							}
						]
					};
					return option;
				},
				{
					// re-attached after every theme flip, since a re-init drops instance listeners
					onChart: (c) => {
						chart = c;
						if (onCellClick) {
							c.on('click', (params: any) => {
								if (params.componentType === 'series' && params.data?.row)
									onCellClick(params.data.row);
							});
						}
					}
				}
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

<div id={chart_id} class="{width} {classesContainer}" style="height: {chartHeight}px"></div>
