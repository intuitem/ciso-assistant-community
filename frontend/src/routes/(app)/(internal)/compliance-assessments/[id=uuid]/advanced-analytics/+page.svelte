<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import StackedBarsNormalized from '$lib/components/Chart/StackedBarsNormalized.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { complianceResultColorMap } from '$lib/utils/constants';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const RESULT_KEYS = [
		'not_assessed',
		'partially_compliant',
		'non_compliant',
		'compliant',
		'not_applicable'
	];
	const RESULT_COLORS = RESULT_KEYS.map((k) => complianceResultColorMap[k]);

	const controlStatusColors: Record<string, string> = {
		'--': '#9ca3af',
		to_do: '#9ca3af',
		in_progress: '#f59e0b',
		on_hold: '#6366f1',
		active: '#22c55e',
		deprecated: '#ef4444'
	};

	const evidenceStatusColors: Record<string, string> = {
		'--': '#9ca3af',
		draft: '#9ca3af',
		missing: '#ef4444',
		in_review: '#f59e0b',
		approved: '#22c55e',
		rejected: '#e11d48'
	};

	function buildSectionChartData(sections: any[]) {
		const chartData = sections.map((s: any) => RESULT_KEYS.map((k) => s.results[k] || 0));
		const names = sections.map((s: any) => (s.ref_id ? s.ref_id + ' ' : '') + s.name);
		return { data: chartData, names };
	}

	function initTimelineChart(el: HTMLElement, timeline: any[]) {
		let chart: any;
		let resizeHandler: (() => void) | null = null;

		import('echarts').then((echarts) => {
			if (!el.isConnected) return;
			chart = echarts.init(el, null, { renderer: 'svg' });
			const dates = timeline.map((t: any) => t.date);
			const hasScores = timeline.some((t: any) => t.score != null && t.score >= 0);
			const areaSeries = RESULT_KEYS.map((key) => ({
				name: safeTranslate(key),
				type: 'line',
				stack: 'total',
				smooth: true,
				showSymbol: false,
				areaStyle: { opacity: 0.5 },
				lineStyle: { width: 1.5 },
				emphasis: { focus: 'series' },
				yAxisIndex: 0,
				data: timeline.map((t: any) => t.per_result[key] || 0),
				itemStyle: { color: complianceResultColorMap[key] }
			}));
			const series: any[] = [...areaSeries];
			if (hasScores) {
				series.push({
					name: safeTranslate('score'),
					type: 'line',
					smooth: true,
					showSymbol: true,
					lineStyle: { width: 2.5 },
					emphasis: { focus: 'series' },
					yAxisIndex: 1,
					data: timeline.map((t: any) => (t.score >= 0 ? t.score : null)),
					itemStyle: { color: '#6366f1' },
					symbol: 'circle',
					symbolSize: 5
				});
			}
			chart.setOption({
				tooltip: {
					trigger: 'axis',
					backgroundColor: '#1e293b',
					borderColor: '#334155',
					textStyle: { color: '#f1f5f9', fontSize: 12 }
				},
				legend: { top: 0, textStyle: { fontSize: 11, color: '#64748b' } },
				grid: { left: 45, right: hasScores ? 50 : 16, top: 36, bottom: 28 },
				xAxis: {
					type: 'category',
					data: dates,
					axisLine: { lineStyle: { color: '#e2e8f0' } },
					axisLabel: { color: '#94a3b8', fontSize: 10 }
				},
				yAxis: [
					{
						type: 'value',
						splitLine: { lineStyle: { color: '#f1f5f9' } },
						axisLabel: { color: '#94a3b8', fontSize: 10 }
					},
					...(hasScores
						? [
								{
									type: 'value',
									position: 'right',
									splitLine: { show: false },
									axisLabel: { color: '#6366f1', fontSize: 10 },
									axisLine: { show: true, lineStyle: { color: '#6366f1' } },
									name: safeTranslate('score'),
									nameTextStyle: { color: '#6366f1', fontSize: 10 }
								}
							]
						: [])
				],
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

<div class="flex flex-col gap-5 pb-8">
	<!-- Header -->
	<div
		class="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-800 via-slate-900 to-indigo-950 px-8 py-6"
	>
		<div
			class="absolute inset-0 opacity-[0.07]"
			style="background-image: radial-gradient(circle at 20% 50%, white 1px, transparent 1px), radial-gradient(circle at 80% 20%, white 1px, transparent 1px); background-size: 32px 32px, 48px 48px;"
		></div>
		<div class="relative">
			<a
				href={`/compliance-assessments/${data.compliance_assessment.id}`}
				class="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors mb-3"
			>
				<i class="fa-solid fa-arrow-left text-[10px]"></i>
				{data.compliance_assessment.name}
			</a>
			<div class="flex items-center gap-3">
				<div
					class="flex items-center justify-center w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm"
				>
					<i class="fa-solid fa-chart-line text-indigo-300 text-lg"></i>
				</div>
				<div>
					<h1 class="text-xl font-semibold text-white tracking-tight">
						{m.advancedAnalytics()}
					</h1>
					<p class="text-xs text-slate-400 mt-0.5">
						{data.compliance_assessment.framework?.name ?? ''}
					</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Compliance Over Time -->
	<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
		<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
			<span
				class="flex items-center justify-center w-7 h-7 rounded-md bg-violet-50 text-violet-500"
			>
				<i class="fa-solid fa-timeline text-xs"></i>
			</span>
			<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
				{m.complianceOverTime()}
			</h2>
		</div>
		<div class="p-6">
			{#await data.stream.complianceTimeline}
				<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
			{:then timelineData}
				{@const timeline = timelineData.timeline}
				{#if timeline && timeline.length > 0}
					<div class="h-72" use:initTimelineChart={timeline}></div>
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

	<!-- Compliance by Section -->
	<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
		<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
			<span class="flex items-center justify-center w-7 h-7 rounded-md bg-blue-50 text-blue-500">
				<i class="fa-solid fa-layer-group text-xs"></i>
			</span>
			<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
				{m.complianceBySection()}
			</h2>
		</div>
		<div class="p-6">
			{#await data.stream.sectionCompliance}
				<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
			{:then sectionData}
				{@const sections = sectionData.sections}
				{#if sections && sections.length > 0}
					{@const chartInfo = buildSectionChartData(sections)}
					<div class="h-[400px]">
						<StackedBarsNormalized
							name="section_compliance"
							data={chartInfo.data}
							names={chartInfo.names}
							uuids={[]}
							colors={RESULT_COLORS}
							seriesNames={RESULT_KEYS.map((k) => safeTranslate(k))}
						/>
					</div>
					{#if sections.some((s: any) => s.scored_count > 0)}
						<div class="mt-5 border-t border-slate-100 pt-5">
							<table class="w-full text-sm">
								<thead>
									<tr class="text-[11px] uppercase tracking-wider text-slate-400">
										<th class="pb-2 pr-4 text-left font-medium">{m.section()}</th>
										<th class="pb-2 pr-4 text-right font-medium">{m.assessable()}</th>
										<th class="pb-2 pr-4 text-right font-medium">{m.score()}</th>
										{#if data.compliance_assessment.show_documentation_score}
											<th class="pb-2 pr-4 text-right font-medium">{m.documentationScore()}</th>
										{/if}
									</tr>
								</thead>
								<tbody>
									{#each sections as section, i}
										<tr class="border-t border-slate-50 {i % 2 === 0 ? 'bg-slate-50/50' : ''}">
											<td class="py-2.5 pr-4 text-slate-700"
												>{section.ref_id ? section.ref_id + ' ' : ''}{section.name}</td
											>
											<td class="py-2.5 pr-4 text-right tabular-nums text-slate-500"
												>{section.total_assessable}</td
											>
											<td class="py-2.5 pr-4 text-right">
												{#if section.score !== null}
													<span
														class="inline-flex items-center justify-center min-w-[2.5rem] rounded-full bg-indigo-50 text-indigo-700 text-xs font-medium px-2 py-0.5"
														>{section.score}</span
													>
												{:else}
													<span class="text-slate-300">&mdash;</span>
												{/if}
											</td>
											{#if data.compliance_assessment.show_documentation_score}
												<td class="py-2.5 pr-4 text-right">
													{#if section.documentation_score !== null}
														<span
															class="inline-flex items-center justify-center min-w-[2.5rem] rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium px-2 py-0.5"
															>{section.documentation_score}</span
														>
													{:else}
														<span class="text-slate-300">&mdash;</span>
													{/if}
												</td>
											{/if}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-slate-400">
						<i class="fa-solid fa-layer-group text-3xl mb-2 opacity-30"></i>
						<p class="text-sm">{m.nothingToShowYet()}</p>
					</div>
				{/if}
			{:catch}
				<p class="text-red-500 text-center py-8 text-sm">{m.anErrorOccurred()}</p>
			{/await}
		</div>
	</section>

	<!-- Coverage Row: Controls + Evidence side by side -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
		<!-- Controls Coverage -->
		<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
			<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
				<span
					class="flex items-center justify-center w-7 h-7 rounded-md bg-emerald-50 text-emerald-500"
				>
					<i class="fa-solid fa-shield-halved text-xs"></i>
				</span>
				<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
					{m.controlsCoverage()}
				</h2>
			</div>
			<div class="p-6">
				{#await data.stream.controlsCoverage}
					<div class="flex items-center justify-center h-48"><LoadingSpinner /></div>
				{:then coverage}
					<!-- Big coverage number -->
					<div class="flex items-center gap-5 mb-5">
						<div
							class="relative flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50"
						>
							<span class="text-2xl font-bold text-emerald-700">{coverage.coverage_percent}%</span>
						</div>
						<div class="flex-1 space-y-2">
							<div class="flex items-center justify-between text-sm">
								<span class="text-slate-500">{m.requirementsWithControls()}</span>
								<span class="font-semibold text-emerald-600 tabular-nums"
									>{coverage.with_controls}</span
								>
							</div>
							<div class="flex items-center justify-between text-sm">
								<span class="text-slate-500">{m.requirementsWithoutControls()}</span>
								<span class="font-semibold text-red-400 tabular-nums"
									>{coverage.without_controls}</span
								>
							</div>
							<!-- Mini bar -->
							{#if coverage.with_controls + coverage.without_controls > 0}
								<div class="flex h-2 rounded-full overflow-hidden bg-red-100">
									<div
										class="bg-emerald-400 rounded-full transition-all"
										style="width: {(coverage.with_controls /
											(coverage.with_controls + coverage.without_controls)) *
											100}%"
									></div>
								</div>
							{/if}
						</div>
					</div>
					<!-- Status distribution inline -->
					{#if Object.keys(coverage.control_status_distribution).length > 0}
						<div class="border-t border-slate-100 pt-4">
							<p class="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-3">
								{safeTranslate('controlStatusDistribution')}
							</p>
							<div class="flex flex-wrap gap-2">
								{#each Object.entries(coverage.control_status_distribution) as [status, count]}
									<span
										class="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
									>
										<span
											class="w-2 h-2 rounded-full"
											style="background-color: {controlStatusColors[status] || '#9ca3af'}"
										></span>
										{safeTranslate(status)}
										<span class="font-semibold text-slate-800">{count}</span>
									</span>
								{/each}
							</div>
						</div>
					{/if}
				{:catch}
					<p class="text-red-500 text-center py-8 text-sm">{m.anErrorOccurred()}</p>
				{/await}
			</div>
		</section>

		<!-- Evidence Coverage -->
		<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
			<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
				<span class="flex items-center justify-center w-7 h-7 rounded-md bg-sky-50 text-sky-500">
					<i class="fa-solid fa-file-circle-check text-xs"></i>
				</span>
				<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
					{m.evidenceCoverage()}
				</h2>
			</div>
			<div class="p-6">
				{#await data.stream.evidenceCoverage}
					<div class="flex items-center justify-center h-48"><LoadingSpinner /></div>
				{:then coverage}
					<div class="flex items-center gap-5 mb-5">
						<div
							class="relative flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-sky-50 to-blue-50"
						>
							<span class="text-2xl font-bold text-sky-700">{coverage.coverage_percent}%</span>
						</div>
						<div class="flex-1 space-y-2">
							<div class="flex items-center justify-between text-sm">
								<span class="text-slate-500">{m.requirementsWithEvidence()}</span>
								<span class="font-semibold text-sky-600 tabular-nums">{coverage.with_evidence}</span
								>
							</div>
							<div class="flex items-center justify-between text-sm">
								<span class="text-slate-500">{m.requirementsWithoutEvidence()}</span>
								<span class="font-semibold text-red-400 tabular-nums"
									>{coverage.without_evidence}</span
								>
							</div>
							{#if coverage.with_evidence + coverage.without_evidence > 0}
								<div class="flex h-2 rounded-full overflow-hidden bg-red-100">
									<div
										class="bg-sky-400 rounded-full transition-all"
										style="width: {(coverage.with_evidence /
											(coverage.with_evidence + coverage.without_evidence)) *
											100}%"
									></div>
								</div>
							{/if}
						</div>
					</div>
					<!-- Evidence type pills -->
					{#if coverage.with_evidence > 0}
						<div class="border-t border-slate-100 pt-4">
							<div class="flex flex-wrap gap-2">
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
								>
									<span class="w-2 h-2 rounded-full bg-blue-400"></span>
									{m.directEvidence()}
									<span class="font-semibold text-slate-800"
										>{coverage.direct_only + coverage.both}</span
									>
								</span>
								<span
									class="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
								>
									<span class="w-2 h-2 rounded-full bg-amber-400"></span>
									{m.indirectEvidence()}
									<span class="font-semibold text-slate-800"
										>{coverage.indirect_only + coverage.both}</span
									>
								</span>
							</div>
						</div>
					{/if}
					<!-- Evidence status distribution -->
					{#if Object.keys(coverage.evidence_status_distribution || {}).length > 0}
						<div class="border-t border-slate-100 pt-4">
							<p class="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-3">
								{safeTranslate('evidenceStatusDistribution')}
							</p>
							<div class="flex flex-wrap gap-2">
								{#each Object.entries(coverage.evidence_status_distribution) as [status, count]}
									<span
										class="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
									>
										<span
											class="w-2 h-2 rounded-full"
											style="background-color: {evidenceStatusColors[status] || '#9ca3af'}"
										></span>
										{safeTranslate(status)}
										<span class="font-semibold text-slate-800">{count}</span>
									</span>
								{/each}
							</div>
						</div>
					{/if}
				{:catch}
					<p class="text-red-500 text-center py-8 text-sm">{m.anErrorOccurred()}</p>
				{/await}
			</div>
		</section>
	</div>

	<!-- Threats & Exceptions Row -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
		<!-- Threats Overview -->
		{#await data.stream.threats then threatsData}
			{#if threatsData.total_unique_threats > 0}
				<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
					<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
						<span
							class="flex items-center justify-center w-7 h-7 rounded-md bg-amber-50 text-amber-500"
						>
							<i class="fa-solid fa-triangle-exclamation text-xs"></i>
						</span>
						<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
							{m.threatsOverview()}
						</h2>
						<span
							class="ml-auto inline-flex items-center rounded-full bg-amber-50 border border-amber-200 px-2.5 py-0.5 text-xs font-semibold text-amber-700"
						>
							{threatsData.total_unique_threats}
						</span>
					</div>
					<div class="p-6">
						{#if threatsData.graph?.nodes}
							{@const sorted = [...threatsData.graph.nodes].sort(
								(a: any, b: any) => b.value - a.value
							)}
							<div class="h-56">
								<BarChart
									name="threats_overview"
									labels={sorted.map((t: any) => t.name)}
									values={sorted.map((t: any) => t.value)}
									horizontal={true}
									title={safeTranslate('affectedRequirements')}
								/>
							</div>
						{/if}
					</div>
				</section>
			{/if}
		{/await}

		<!-- Exceptions Overview -->
		{#await data.stream.exceptions then exceptionsData}
			{#if exceptionsData.total > 0}
				<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
					<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
						<span
							class="flex items-center justify-center w-7 h-7 rounded-md bg-purple-50 text-purple-500"
						>
							<i class="fa-solid fa-file-shield text-xs"></i>
						</span>
						<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
							{m.exceptionsOverview()}
						</h2>
						<span
							class="ml-auto inline-flex items-center rounded-full bg-purple-50 border border-purple-200 px-2.5 py-0.5 text-xs font-semibold text-purple-700"
						>
							{exceptionsData.total}
						</span>
					</div>
					<div class="p-6">
						<div class="grid grid-cols-2 gap-4">
							<div class="h-48">
								{#if Object.keys(exceptionsData.status_distribution).length > 0}
									{@const statusEntries = Object.entries(exceptionsData.status_distribution)}
									<DonutChart
										name="exception_status"
										values={statusEntries.map(([k, v]) => ({
											name: safeTranslate(k),
											value: v
										}))}
									/>
								{:else}
									<div class="flex items-center justify-center h-full text-sm text-slate-400">
										{m.nothingToShowYet()}
									</div>
								{/if}
							</div>
							<div class="h-48">
								{#if Object.keys(exceptionsData.severity_distribution).length > 0}
									{@const sevEntries = Object.entries(exceptionsData.severity_distribution)}
									<BarChart
										name="exception_severity"
										labels={sevEntries.map(([k]) => safeTranslate(k))}
										values={sevEntries.map(([, v]) => v)}
										title={safeTranslate('severity')}
									/>
								{:else}
									<div class="flex items-center justify-center h-full text-sm text-slate-400">
										{m.nothingToShowYet()}
									</div>
								{/if}
							</div>
						</div>
					</div>
				</section>
			{/if}
		{/await}
	</div>

	<!-- Implementation Groups Breakdown -->
	<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
		<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
			<span
				class="flex items-center justify-center w-7 h-7 rounded-md bg-orange-50 text-orange-500"
			>
				<i class="fa-solid fa-cubes text-xs"></i>
			</span>
			<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
				{m.implementationGroupsBreakdown()}
			</h2>
		</div>
		<div class="p-6">
			{#await data.stream.igBreakdown}
				<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
			{:then igData}
				{@const groups = igData.groups}
				{#if groups && groups.length > 0}
					{@const chartInfo = (() => {
						const chartData = groups.map((g: any) => RESULT_KEYS.map((k) => g.results[k] || 0));
						const names = groups.map((g: any) => g.name || g.ref_id);
						return { data: chartData, names };
					})()}
					<div class="h-[350px]">
						<StackedBarsNormalized
							name="ig_breakdown"
							data={chartInfo.data}
							names={chartInfo.names}
							uuids={[]}
							colors={RESULT_COLORS}
							seriesNames={RESULT_KEYS.map((k) => safeTranslate(k))}
						/>
					</div>
					<div class="mt-5 border-t border-slate-100 pt-5">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-[11px] uppercase tracking-wider text-slate-400">
									<th class="pb-2 pr-4 text-left font-medium">{m.name()}</th>
									<th class="pb-2 pr-4 text-right font-medium">{m.assessable()}</th>
									<th class="pb-2 pr-4 text-right font-medium">{m.progress()}</th>
									<th class="pb-2 pr-4 text-right font-medium">{m.score()}</th>
									{#if data.compliance_assessment.show_documentation_score}
										<th class="pb-2 pr-4 text-right font-medium">{m.documentationScore()}</th>
									{/if}
								</tr>
							</thead>
							<tbody>
								{#each groups as group, i}
									<tr class="border-t border-slate-50 {i % 2 === 0 ? 'bg-slate-50/50' : ''}">
										<td class="py-2.5 pr-4 text-slate-700">{group.name || group.ref_id}</td>
										<td class="py-2.5 pr-4 text-right tabular-nums text-slate-500"
											>{group.total_assessable}</td
										>
										<td class="py-2.5 pr-4 text-right">
											<div class="inline-flex items-center gap-1.5 text-xs text-slate-600">
												<div class="w-12 h-1.5 rounded-full bg-slate-100 overflow-hidden">
													<div
														class="h-full rounded-full bg-indigo-400"
														style="width: {group.progress_percent}%"
													></div>
												</div>
												<span class="tabular-nums">{group.progress_percent}%</span>
											</div>
										</td>
										<td class="py-2.5 pr-4 text-right">
											{#if group.score !== null}
												<span
													class="inline-flex items-center justify-center min-w-[2.5rem] rounded-full bg-indigo-50 text-indigo-700 text-xs font-medium px-2 py-0.5"
													>{group.score}</span
												>
											{:else}
												<span class="text-slate-300">&mdash;</span>
											{/if}
										</td>
										{#if data.compliance_assessment.show_documentation_score}
											<td class="py-2.5 pr-4 text-right">
												{#if group.documentation_score !== null}
													<span
														class="inline-flex items-center justify-center min-w-[2.5rem] rounded-full bg-emerald-50 text-emerald-700 text-xs font-medium px-2 py-0.5"
														>{group.documentation_score}</span
													>
												{:else}
													<span class="text-slate-300">&mdash;</span>
												{/if}
											</td>
										{/if}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-slate-400">
						<i class="fa-solid fa-cubes text-3xl mb-2 opacity-30"></i>
						<p class="text-sm">{m.noImplementationGroups()}</p>
					</div>
				{/if}
			{:catch}
				<p class="text-red-500 text-center py-8 text-sm">{m.anErrorOccurred()}</p>
			{/await}
		</div>
	</section>

	<!-- Mapping Projection -->
	<section class="rounded-xl border border-slate-200 bg-white overflow-hidden">
		<div class="border-b border-slate-100 px-6 py-4 flex items-center gap-2.5">
			<span class="flex items-center justify-center w-7 h-7 rounded-md bg-rose-50 text-rose-500">
				<i class="fa-solid fa-diagram-project text-xs"></i>
			</span>
			<h2 class="text-sm font-semibold text-slate-800 tracking-tight">
				{m.mappingProjection()}
			</h2>
		</div>
		<div class="p-6">
			{#await data.stream.mappingProjection}
				<div class="flex items-center justify-center h-48"><LoadingSpinner /></div>
			{:then frameworks}
				{#if frameworks && frameworks.length > 0}
					<div class="space-y-3">
						{#each frameworks as fw}
							<div class="rounded-lg border border-slate-100 bg-slate-50/50 p-4">
								<div class="flex items-center justify-between mb-2.5">
									<span class="text-sm font-medium text-slate-700">{fw.str}</span>
									<span class="text-[11px] text-slate-400 tabular-nums font-medium"
										>{fw.assessable_requirements_count} {m.assessable()}</span
									>
								</div>
								{#if Object.values(fw.results || {}).reduce((a, b) => a + (b as number), 0) > 0}
									{@const results = fw.results || {}}
									{@const total = Object.values(results).reduce(
										(a: number, b: any) => a + (b as number),
										0
									)}
									<div class="flex h-5 rounded-md overflow-hidden gap-px">
										{#each RESULT_KEYS as key}
											{@const count = results[key] || 0}
											{@const pct = (count / total) * 100}
											{#if pct > 0}
												<div
													class="flex items-center justify-center text-[10px] font-medium transition-all first:rounded-l-md last:rounded-r-md"
													style="width: {pct}%; background-color: {complianceResultColorMap[
														key
													]}; {key === 'not_applicable'
														? 'color: white;'
														: 'color: rgba(0,0,0,0.5);'}"
													title="{safeTranslate(key)}: {count} ({pct.toFixed(1)}%)"
												>
													{#if pct > 8}{Math.round(pct)}%{/if}
												</div>
											{/if}
										{/each}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12 text-slate-400">
						<i class="fa-solid fa-diagram-project text-3xl mb-2 opacity-30"></i>
						<p class="text-sm">{m.noMappingTargets()}</p>
					</div>
				{/if}
			{:catch}
				<p class="text-red-500 text-center py-8 text-sm">{m.anErrorOccurred()}</p>
			{/await}
		</div>
	</section>
</div>
