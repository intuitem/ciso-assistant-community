<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		results?: any[];
		assets?: { id: string; name: string }[];
		width?: string;
		classesContainer?: string;
		name?: string;
	}

	let {
		results = [],
		assets = [],
		width = 'w-full',
		classesContainer = '',
		name = 'posture_heatmap'
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

	const chartHeight = $derived(Math.max(280, checks.length * 24 + 120));

	onMount(async () => {
		const echarts = await import('echarts');
		const chart = echarts.init(
			document.getElementById(chart_id),
			document.documentElement.classList.contains('dark') ? 'dark' : null,
			{ renderer: 'svg' }
		);

		const latestTimestamp = results.reduce((acc, r) => (r.timestamp > acc ? r.timestamp : acc), '');
		const assetIndex = new Map(assets.map((a, i) => [a.id, i]));
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

		const option = {
			backgroundColor: 'transparent',
			grid: { top: 30, right: 10, bottom: 60, left: 90 },
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
					return parts.join('<br/>');
				}
			},
			xAxis: {
				type: 'category',
				data: assets.map((a) => a.name),
				position: 'top',
				axisLabel: { interval: 0, rotate: assets.length > 6 ? 30 : 0 },
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

		chart.setOption(option);
		window.addEventListener('resize', () => chart.resize());
	});
</script>

<div id={chart_id} class="{width} {classesContainer}" style="height: {chartHeight}px"></div>
