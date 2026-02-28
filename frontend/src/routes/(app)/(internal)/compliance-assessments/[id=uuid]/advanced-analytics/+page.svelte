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

	function buildSectionChartData(sections: any[]) {
		// data: array of arrays (one per audit/bar), each inner array has counts per result category
		const chartData = sections.map((s: any) => RESULT_KEYS.map((k) => s.results[k] || 0));
		const names = sections.map((s: any) => (s.ref_id ? s.ref_id + ' ' : '') + s.name);
		return { data: chartData, names };
	}
</script>

<div class="flex flex-col space-y-6">
	<div class="flex items-center space-x-3">
		<a
			href={`/compliance-assessments/${data.compliance_assessment.id}`}
			class="text-sm text-indigo-600 hover:underline"
		>
			&larr; {data.compliance_assessment.name}
		</a>
	</div>

	<!-- Section 1: Compliance by Section -->
	<div class="card bg-white shadow-lg p-6">
		<h2 class="text-lg font-semibold mb-4">{m.complianceBySection()}</h2>
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
				<!-- Score table -->
				{#if sections.some((s: any) => s.scored_count > 0)}
					<div class="mt-4 overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b text-left text-gray-500">
									<th class="py-2 pr-4">{m.section()}</th>
									<th class="py-2 pr-4 text-right">{m.assessable()}</th>
									<th class="py-2 pr-4 text-right">{m.avgScore()}</th>
									{#if data.compliance_assessment.show_documentation_score}
										<th class="py-2 pr-4 text-right">{m.avgDocumentationScore()}</th>
									{/if}
								</tr>
							</thead>
							<tbody>
								{#each sections as section}
									<tr class="border-b border-gray-100">
										<td class="py-2 pr-4 font-medium"
											>{section.ref_id ? section.ref_id + ' ' : ''}{section.name}</td
										>
										<td class="py-2 pr-4 text-right">{section.total_assessable}</td>
										<td class="py-2 pr-4 text-right">
											{#if section.avg_score !== null}
												<span class="badge preset-filled-primary-500 text-xs"
													>{section.avg_score}</span
												>
											{:else}
												<span class="text-gray-400">-</span>
											{/if}
										</td>
										{#if data.compliance_assessment.show_documentation_score}
											<td class="py-2 pr-4 text-right">
												{#if section.avg_documentation_score !== null}
													<span class="badge preset-filled-secondary-500 text-xs"
														>{section.avg_documentation_score}</span
													>
												{:else}
													<span class="text-gray-400">-</span>
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
				<p class="text-gray-500 text-center py-8">{m.nothingToShowYet()}</p>
			{/if}
		{:catch}
			<p class="text-red-500 text-center py-8">{m.anErrorOccurred()}</p>
		{/await}
	</div>

	<!-- Section 2: Controls Coverage -->
	<div class="card bg-white shadow-lg p-6">
		<h2 class="text-lg font-semibold mb-4">{m.controlsCoverage()}</h2>
		{#await data.stream.controlsCoverage}
			<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
		{:then coverage}
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				<!-- Summary cards -->
				<div class="flex flex-col space-y-3">
					<div class="rounded-lg border p-4 text-center">
						<div class="text-3xl font-bold text-indigo-600">{coverage.coverage_percent}%</div>
						<div class="text-sm text-gray-500 mt-1">{m.coveragePercent()}</div>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<div class="rounded-lg border p-3 text-center">
							<div class="text-xl font-semibold text-green-600">{coverage.with_controls}</div>
							<div class="text-xs text-gray-500">{m.requirementsWithControls()}</div>
						</div>
						<div class="rounded-lg border p-3 text-center">
							<div class="text-xl font-semibold text-red-500">{coverage.without_controls}</div>
							<div class="text-xs text-gray-500">{m.requirementsWithoutControls()}</div>
						</div>
					</div>
				</div>

				<!-- Donut: with/without controls -->
				<div class="h-64">
					<DonutChart
						name="controls_coverage"
						values={[
							{
								name: safeTranslate('requirementsWithControls'),
								value: coverage.with_controls
							},
							{
								name: safeTranslate('requirementsWithoutControls'),
								value: coverage.without_controls
							}
						]}
						colors={['#22c55e', '#ef4444']}
					/>
				</div>

				<!-- Control status distribution -->
				<div class="h-64">
					{#if Object.keys(coverage.control_status_distribution).length > 0}
						{@const statusEntries = Object.entries(coverage.control_status_distribution)}
						<BarChart
							name="control_status"
							labels={statusEntries.map(([k]) => safeTranslate(k))}
							values={statusEntries.map(([, v]) => v)}
							title={safeTranslate('controlStatusDistribution')}
						/>
					{:else}
						<p class="text-gray-500 text-center py-8">{m.nothingToShowYet()}</p>
					{/if}
				</div>
			</div>
		{:catch}
			<p class="text-red-500 text-center py-8">{m.anErrorOccurred()}</p>
		{/await}
	</div>

	<!-- Section 3: Evidence Coverage -->
	<div class="card bg-white shadow-lg p-6">
		<h2 class="text-lg font-semibold mb-4">{m.evidenceCoverage()}</h2>
		{#await data.stream.evidenceCoverage}
			<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
		{:then coverage}
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				<!-- Summary cards -->
				<div class="flex flex-col space-y-3">
					<div class="rounded-lg border p-4 text-center">
						<div class="text-3xl font-bold text-indigo-600">{coverage.coverage_percent}%</div>
						<div class="text-sm text-gray-500 mt-1">{m.coveragePercent()}</div>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<div class="rounded-lg border p-3 text-center">
							<div class="text-xl font-semibold text-green-600">{coverage.with_evidence}</div>
							<div class="text-xs text-gray-500">{m.requirementsWithEvidence()}</div>
						</div>
						<div class="rounded-lg border p-3 text-center">
							<div class="text-xl font-semibold text-red-500">{coverage.without_evidence}</div>
							<div class="text-xs text-gray-500">{m.requirementsWithoutEvidence()}</div>
						</div>
					</div>
				</div>

				<!-- Donut: with/without evidence -->
				<div class="h-64">
					<DonutChart
						name="evidence_coverage"
						values={[
							{
								name: safeTranslate('requirementsWithEvidence'),
								value: coverage.with_evidence
							},
							{
								name: safeTranslate('requirementsWithoutEvidence'),
								value: coverage.without_evidence
							}
						]}
						colors={['#22c55e', '#ef4444']}
					/>
				</div>

				<!-- Evidence status distribution -->
				<div class="h-64">
					{#if Object.keys(coverage.evidence_status_distribution).length > 0}
						{@const statusEntries = Object.entries(coverage.evidence_status_distribution)}
						<BarChart
							name="evidence_status"
							labels={statusEntries.map(([k]) => safeTranslate(k))}
							values={statusEntries.map(([, v]) => v)}
							title={safeTranslate('evidenceStatusDistribution')}
						/>
					{:else}
						<p class="text-gray-500 text-center py-8">{m.nothingToShowYet()}</p>
					{/if}
				</div>
			</div>

			<!-- Evidence type breakdown -->
			{#if coverage.with_evidence > 0}
				<div class="mt-4 flex items-center justify-center gap-6 text-sm text-gray-600">
					<span class="flex items-center gap-1">
						<span class="inline-block w-3 h-3 rounded-full bg-blue-500"></span>
						{m.directEvidence()}: {coverage.direct_only}
					</span>
					<span class="flex items-center gap-1">
						<span class="inline-block w-3 h-3 rounded-full bg-amber-500"></span>
						{m.indirectEvidence()}: {coverage.indirect_only}
					</span>
					<span class="flex items-center gap-1">
						<span class="inline-block w-3 h-3 rounded-full bg-green-500"></span>
						{m.bothEvidenceTypes()}: {coverage.both}
					</span>
				</div>
			{/if}
		{:catch}
			<p class="text-red-500 text-center py-8">{m.anErrorOccurred()}</p>
		{/await}
	</div>

	<!-- Section 4: Threats Overview -->
	{#await data.stream.threats then threatsData}
		{#if threatsData.total_unique_threats > 0}
			<div class="card bg-white shadow-lg p-6">
				<h2 class="text-lg font-semibold mb-4">{m.threatsOverview()}</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
					<div class="flex flex-col space-y-3">
						<div class="rounded-lg border p-4 text-center">
							<div class="text-3xl font-bold text-orange-600">
								{threatsData.total_unique_threats}
							</div>
							<div class="text-sm text-gray-500 mt-1">{m.uniqueThreats()}</div>
						</div>
					</div>
					<div class="md:col-span-2 h-64">
						{#if threatsData.graph?.nodes}
							{@const sorted = [...threatsData.graph.nodes].sort(
								(a: any, b: any) => b.value - a.value
							)}
							<BarChart
								name="threats_overview"
								labels={sorted.map((t: any) => t.name)}
								values={sorted.map((t: any) => t.value)}
								horizontal={true}
								title={safeTranslate('affectedRequirements')}
							/>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	{/await}

	<!-- Section 5: Exceptions Overview -->
	{#await data.stream.exceptions then exceptionsData}
		{#if exceptionsData.total > 0}
			<div class="card bg-white shadow-lg p-6">
				<h2 class="text-lg font-semibold mb-4">{m.exceptionsOverview()}</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
					<div class="flex flex-col space-y-3">
						<div class="rounded-lg border p-4 text-center">
							<div class="text-3xl font-bold text-purple-600">
								{exceptionsData.total}
							</div>
							<div class="text-sm text-gray-500 mt-1">{m.totalExceptions()}</div>
						</div>
					</div>
					<!-- Status distribution donut -->
					<div class="h-64">
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
							<p class="text-gray-500 text-center py-8">{m.nothingToShowYet()}</p>
						{/if}
					</div>
					<!-- Severity distribution bar -->
					<div class="h-64">
						{#if Object.keys(exceptionsData.severity_distribution).length > 0}
							{@const sevEntries = Object.entries(exceptionsData.severity_distribution)}
							<BarChart
								name="exception_severity"
								labels={sevEntries.map(([k]) => safeTranslate(k))}
								values={sevEntries.map(([, v]) => v)}
								title={safeTranslate('severity')}
							/>
						{:else}
							<p class="text-gray-500 text-center py-8">{m.nothingToShowYet()}</p>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	{/await}

	<!-- Compliance Over Time -->
	<div class="card bg-white shadow-lg p-6">
		<h2 class="text-lg font-semibold mb-4">{m.complianceOverTime()}</h2>
		{#await data.stream.complianceTimeline}
			<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
		{:then timelineData}
			{@const timeline = timelineData.timeline}
			{#if timeline && timeline.length > 0}
				<div class="h-80" id="timeline_chart_container">
					<!-- Inline ECharts for timeline -->
					{#await import('echarts') then echarts}
						{@const _init = (() => {
							setTimeout(() => {
								const el = document.getElementById('timeline_chart_container');
								if (!el) return;
								const chart = echarts.init(el, null, { renderer: 'svg' });
								const dates = timeline.map((t: any) => t.date);
								const series = RESULT_KEYS.map((key) => ({
									name: safeTranslate(key),
									type: 'line',
									stack: 'total',
									smooth: true,
									showSymbol: false,
									areaStyle: { opacity: 0.6 },
									emphasis: { focus: 'series' },
									data: timeline.map((t: any) => t.per_result[key] || 0),
									itemStyle: { color: complianceResultColorMap[key] }
								}));
								chart.setOption({
									tooltip: { trigger: 'axis' },
									legend: { top: 0 },
									grid: { left: 50, right: 20, top: 40, bottom: 30 },
									xAxis: { type: 'category', data: dates },
									yAxis: { type: 'value' },
									series
								});
								window.addEventListener('resize', () => chart.resize());
							}, 0);
							return '';
						})()}
					{/await}
				</div>
			{:else}
				<p class="text-gray-500 text-center py-8">{m.nothingToShowYet()}</p>
			{/if}

			<!-- Comparable audits -->
			{@const comparable = timelineData.comparable_audits}
			{#if comparable && comparable.length > 0}
				<div class="mt-6">
					<h3 class="text-md font-semibold mb-3">{m.comparableAudits()}</h3>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b text-left text-gray-500">
									<th class="py-2 pr-4">{m.name()}</th>
									<th class="py-2 pr-4 text-right">{m.progress()}</th>
									<th class="py-2 pr-4 text-right">{m.score()}</th>
									<th class="py-2 pr-4 text-right">{safeTranslate('compliant')}</th>
									<th class="py-2 pr-4 text-right">{safeTranslate('nonCompliant')}</th>
								</tr>
							</thead>
							<tbody>
								{#each comparable as audit}
									<tr class="border-b border-gray-100">
										<td class="py-2 pr-4">
											<a
												href={`/compliance-assessments/${audit.id}`}
												class="text-indigo-600 hover:underline">{audit.name}</a
											>
										</td>
										<td class="py-2 pr-4 text-right">{audit.final_progress}%</td>
										<td class="py-2 pr-4 text-right">{audit.final_score ?? '-'}</td>
										<td class="py-2 pr-4 text-right">{audit.final_per_result?.compliant ?? 0}</td>
										<td class="py-2 pr-4 text-right"
											>{audit.final_per_result?.non_compliant ?? 0}</td
										>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/if}
		{:catch}
			<p class="text-red-500 text-center py-8">{m.anErrorOccurred()}</p>
		{/await}
	</div>

	<!-- Section 4: Implementation Groups Breakdown -->
	<div class="card bg-white shadow-lg p-6">
		<h2 class="text-lg font-semibold mb-4">{m.implementationGroupsBreakdown()}</h2>
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
				<!-- Score and progress table -->
				<div class="mt-4 overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="border-b text-left text-gray-500">
								<th class="py-2 pr-4">{m.name()}</th>
								<th class="py-2 pr-4 text-right">{m.assessable()}</th>
								<th class="py-2 pr-4 text-right">{m.progress()}</th>
								<th class="py-2 pr-4 text-right">{m.avgScore()}</th>
								{#if data.compliance_assessment.show_documentation_score}
									<th class="py-2 pr-4 text-right">{m.avgDocumentationScore()}</th>
								{/if}
							</tr>
						</thead>
						<tbody>
							{#each groups as group}
								<tr class="border-b border-gray-100">
									<td class="py-2 pr-4 font-medium">{group.name || group.ref_id}</td>
									<td class="py-2 pr-4 text-right">{group.total_assessable}</td>
									<td class="py-2 pr-4 text-right">{group.progress_percent}%</td>
									<td class="py-2 pr-4 text-right">
										{#if group.avg_score !== null}
											<span class="badge preset-filled-primary-500 text-xs">{group.avg_score}</span>
										{:else}
											<span class="text-gray-400">-</span>
										{/if}
									</td>
									{#if data.compliance_assessment.show_documentation_score}
										<td class="py-2 pr-4 text-right">
											{#if group.avg_documentation_score !== null}
												<span class="badge preset-filled-secondary-500 text-xs"
													>{group.avg_documentation_score}</span
												>
											{:else}
												<span class="text-gray-400">-</span>
											{/if}
										</td>
									{/if}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-gray-500 text-center py-8">{m.noImplementationGroups()}</p>
			{/if}
		{:catch}
			<p class="text-red-500 text-center py-8">{m.anErrorOccurred()}</p>
		{/await}
	</div>

	<!-- Section 5: Mapping Projection -->
	<div class="card bg-white shadow-lg p-6">
		<h2 class="text-lg font-semibold mb-4">{m.mappingProjection()}</h2>
		{#await data.stream.mappingProjection}
			<div class="flex items-center justify-center h-64"><LoadingSpinner /></div>
		{:then frameworks}
			{#if frameworks && frameworks.length > 0}
				<div class="space-y-4">
					{#each frameworks as fw}
						<div class="border rounded-lg p-4">
							<div class="flex items-center justify-between mb-2">
								<span class="font-medium text-sm">{fw.str}</span>
								<span class="text-xs text-gray-500"
									>{fw.assessable_requirements_count} {m.assessable()}</span
								>
							</div>
							<!-- Stacked progress bar -->
							{#if Object.values(fw.results || {}).reduce((a, b) => a + (b as number), 0) > 0}
								{@const results = fw.results || {}}
								{@const total = Object.values(results).reduce(
									(a: number, b: any) => a + (b as number),
									0
								)}
								<div class="flex h-6 rounded-full overflow-hidden">
									{#each RESULT_KEYS as key}
										{@const count = results[key] || 0}
										{@const pct = (count / total) * 100}
										{#if pct > 0}
											<div
												class="flex items-center justify-center text-[10px] font-medium"
												style="width: {pct}%; background-color: {complianceResultColorMap[
													key
												]}; {key === 'not_applicable' ? 'color: white;' : ''}"
												title="{safeTranslate(key)}: {count} ({pct.toFixed(1)}%)"
											>
												{#if pct > 5}{Math.round(pct)}%{/if}
											</div>
										{/if}
									{/each}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-gray-500 text-center py-8">{m.noMappingTargets()}</p>
			{/if}
		{:catch}
			<p class="text-red-500 text-center py-8">{m.anErrorOccurred()}</p>
		{/await}
	</div>
</div>
