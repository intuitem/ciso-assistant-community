<script lang="ts">
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	let { data } = $props();

	const treatmentColors: Record<string, string> = {
		open: '#94a3b8',
		mitigate: '#3b82f6',
		accept: '#22c55e',
		avoid: '#f59e0b',
		transfer: '#a855f7'
	};

	// SOK labels come as "low", "medium", "high" — sorted by level ascending
	const sokColors: Record<string, string> = {
		low: '#f87171',
		medium: '#fbbf24',
		high: '#34d399'
	};

	function initTimelineChart(
		el: HTMLElement,
		params: { timeline: any[]; colors: Record<string, string> }
	) {
		let chart: any;
		let resizeHandler: (() => void) | null = null;

		import('echarts').then((echarts) => {
			if (!el.isConnected) return;
			chart = echarts.init(el, null, { renderer: 'svg' });

			const { timeline, colors } = params;
			const dates = timeline.map((t: any) => t.date);

			// Collect all risk level names across all snapshots
			const levelSet = new Set<string>();
			for (const t of timeline) {
				for (const key of Object.keys(t.current_level_breakdown || {})) {
					levelSet.add(key);
				}
			}
			const levelNames = [...levelSet];

			const series = levelNames.map((level) => ({
				name: safeTranslate(level),
				type: 'line' as const,
				stack: 'risk',
				smooth: true,
				showSymbol: false,
				areaStyle: { opacity: 0.6 },
				lineStyle: { width: 1.5 },
				emphasis: { focus: 'series' as const },
				data: timeline.map((t: any) => t.current_level_breakdown?.[level] || 0),
				itemStyle: { color: colors[level] ?? '#6b7280' }
			}));

			chart.setOption({
				tooltip: {
					trigger: 'axis',
					backgroundColor: '#1e293b',
					borderColor: '#334155',
					textStyle: { color: '#f1f5f9', fontSize: 12 }
				},
				legend: { top: 0, textStyle: { fontSize: 11, color: '#64748b' } },
				grid: { left: 45, right: 16, top: 36, bottom: 28 },
				xAxis: {
					type: 'category',
					data: dates,
					axisLine: { lineStyle: { color: '#e2e8f0' } },
					axisLabel: { color: '#94a3b8', fontSize: 10 }
				},
				yAxis: {
					type: 'value',
					splitLine: { lineStyle: { color: '#f1f5f9' } },
					axisLabel: { color: '#94a3b8', fontSize: 10 }
				},
				series
			});

			resizeHandler = () => chart.resize();
			window.addEventListener('resize', resizeHandler);
		});

		return {
			destroy() {
				if (resizeHandler) window.removeEventListener('resize', resizeHandler);
				if (chart) chart.dispose();
			}
		};
	}
</script>

<div class="space-y-6 p-6">
	<!-- Header -->
	<div class="flex items-center gap-4">
		<Anchor
			href="/risk-assessments/{data.risk_assessment.id}"
			breadcrumbAction="pop"
			class="flex items-center justify-center w-9 h-9 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors text-gray-600"
		>
			<i class="fa-solid fa-arrow-left text-sm"></i>
		</Anchor>
		<div>
			<h1 class="text-xl font-bold text-gray-900">{m.analytics()}</h1>
			<p class="text-sm text-gray-500">
				{data.risk_assessment.name} - {data.risk_assessment.version}
			</p>
		</div>
	</div>

	<!-- Risk Levels Over Time -->
	<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
		<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
			<span
				class="flex items-center justify-center w-7 h-7 rounded-md bg-violet-50 text-violet-500"
			>
				<i class="fa-solid fa-timeline text-xs"></i>
			</span>
			<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
				{m.riskLevelsOverTime()}
			</h2>
		</div>
		<div class="p-6">
			{#await data.stream.timeline}
				<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
			{:then timelineData}
				{#if timelineData.timeline && timelineData.timeline.length > 1}
					<div
						class="h-72"
						use:initTimelineChart={{
							timeline: timelineData.timeline,
							colors: timelineData.risk_level_colors ?? {}
						}}
					></div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-slate-400">
						<i class="fa-solid fa-chart-area text-3xl mb-2 opacity-30"></i>
						<p class="text-sm">{m.nothingToShowYet()}</p>
					</div>
				{/if}
			{:catch}
				<p class="text-red-500 text-center py-8 text-sm">{m.anErrorOccurred()}</p>
			{/await}
		</div>
	</section>

	{#await data.stream.analytics}
		<div class="flex items-center justify-center py-20">
			<LoadingSpinner />
		</div>
	{:then analytics}
		<!-- Row 1: Threat Radar + Treatment Distribution -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Threat Radar / Bar -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.threatsBreakdown()}</h3>
				{#if analytics.threats?.labels?.length > 0}
					{#if analytics.threats.labels.length <= 10}
						<div class="h-80">
							<RadarChart
								name="threatRadar"
								labels={analytics.threats.labels}
								values={analytics.threats.values}
							/>
						</div>
					{:else}
						{@const threatLabels = [...analytics.threats.labels]
							.reverse()
							.map((l) => safeTranslate(l.name))}
						{@const threatValues = [...analytics.threats.values].reverse()}
						<div class="overflow-y-auto max-h-80">
							<div style="height: {Math.max(224, threatLabels.length * 28)}px">
								<BarChart
									name="threatBar"
									labels={threatLabels}
									values={threatValues}
									horizontal={true}
								/>
							</div>
						</div>
					{/if}
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noThreatsMapped()}</p>
					</div>
				{/if}
			</div>

			<!-- Treatment Distribution -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.treatmentDistribution()}</h3>
				{#if analytics.treatment?.labels?.length > 0}
					{@const treatmentValues = analytics.treatment.labels.map((label, i) => ({
						name: label,
						value: analytics.treatment.values[i]
					}))}
					<div class="h-80">
						<DonutChart
							name="treatmentDonut"
							values={treatmentValues}
							colors={treatmentValues.map((t) => treatmentColors[t.name] ?? '#6b7280')}
						/>
					</div>
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noDataAvailable()}</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- Row 2: Strength of Knowledge + Assets at Risk -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Strength of Knowledge -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.strengthOfKnowledge()}</h3>
				{#if analytics.strength_of_knowledge?.labels?.length > 0}
					{@const sokValues = analytics.strength_of_knowledge.labels.map((label, i) => ({
						name: label,
						value: analytics.strength_of_knowledge.values[i]
					}))}
					<div class="h-80">
						<DonutChart
							name="sokDonut"
							values={sokValues}
							colors={sokValues.map((s) => sokColors[s.name] ?? '#6b7280')}
						/>
					</div>
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noDataAvailable()}</p>
					</div>
				{/if}
			</div>

			<!-- Assets at Risk -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.assetsAtRisk()}</h3>
				{#if analytics.assets?.labels?.length > 0}
					<div class="h-80">
						<BarChart
							name="assetsBar"
							labels={[...analytics.assets.labels].reverse()}
							values={[...analytics.assets.values].reverse()}
							horizontal={true}
						/>
					</div>
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noDataAvailable()}</p>
					</div>
				{/if}
			</div>
		</div>
	{:catch}
		<div class="text-red-500 text-center py-12">
			<p>{m.anErrorOccurred()}</p>
		</div>
	{/await}
</div>
