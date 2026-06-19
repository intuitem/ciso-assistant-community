<script lang="ts">
	import { page } from '$app/state';
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RingProgress from '$lib/components/DataViz/RingProgress.svelte';
	import { displayScoreColor, getScoreHexColor } from '$lib/utils/helpers';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import ComparisonRadarChart from '$lib/components/Chart/ComparisonRadarChart.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const fieldsToCompare = [
		{ key: 'name', label: 'Name' },
		{ key: 'version', label: 'Version' },
		{ key: 'perimeter', label: 'Perimeter' },
		{ key: 'status', label: 'Status' },
		{ key: 'selected_implementation_groups', label: 'Implementation Groups' },
		{ key: 'created_at', label: 'Created At', format: 'date' },
		{ key: 'updated_at', label: 'Last Update', format: 'date' },
		{ key: 'observation', label: 'Observation', format: 'markdown' }
	];

	function getFieldValue(audit: any, field: any) {
		const value = audit[field.key];

		if (!value) return '--';

		if (field.format === 'date') {
			return formatDateOrDateTime(value, getLocale());
		}

		if (Array.isArray(value)) {
			if (value.length === 0) return '--';
			return value.map((v) => (v.str ? v.str : v)).join(', ');
		}

		if (value.str) return value.str;

		return safeTranslate(value);
	}
</script>

<div class="flex flex-col space-y-4">
	<div class="card p-4 bg-surface-50-950 shadow-lg">
		<div class="flex items-center justify-between mb-4">
			<div class="flex flex-col">
				<div class="h4 font-bold">
					<i class="fa-solid fa-code-compare mr-2"></i>
					{m.complianceAssessmentComparison()}
				</div>
				<div class="text-sm text-surface-600-400 mt-1">
					<span class="font-medium">{m.framework()}:</span>
					{data.framework.str}
				</div>
			</div>
			<Anchor
				href="/compliance-assessments/{data.baseAudit.id}"
				class="btn preset-filled-primary-500"
			>
				<i class="fa-solid fa-arrow-left mr-2"></i>
				{m.backToBaseAudit()}
			</Anchor>
		</div>
	</div>

	<div class="card bg-surface-50-950 shadow-lg">
		<div class="grid grid-cols-2 divide-x divide-surface-200-800">
			<!-- Left side: Base Audit -->
			<div class="p-6 space-y-4">
				<div class="flex items-center justify-between mb-4">
					<h2 class="h4 font-bold text-primary-500">{m.baseAudit()}</h2>
					<Anchor
						href="/compliance-assessments/{data.baseAudit.id}"
						class="btn btn-sm preset-filled-secondary-500"
					>
						<i class="fa-solid fa-external-link-alt mr-2"></i>
						{m.view()}
					</Anchor>
				</div>

				{#each fieldsToCompare as field}
					<div class="flex flex-col">
						<div class="text-sm font-medium text-surface-600-400">{safeTranslate(field.key)}</div>
						{#if field.format === 'markdown'}
							<div class="text-base text-surface-950-50">
								{#if data.baseAudit[field.key]}
									<MarkdownRenderer content={data.baseAudit[field.key]} />
								{:else}
									--
								{/if}
							</div>
						{:else}
							<div class="text-base font-semibold text-surface-950-50">
								{getFieldValue(data.baseAudit, field)}
							</div>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Right side: Comparison Audit -->
			<div class="p-6 space-y-4">
				<div class="flex items-center justify-between mb-4">
					<h2 class="h4 font-bold text-secondary-500">{m.comparisonAudit()}</h2>
					<Anchor
						href="/compliance-assessments/{data.compareAudit.id}"
						class="btn btn-sm preset-filled-secondary-500"
					>
						<i class="fa-solid fa-external-link-alt mr-2"></i>
						{m.view()}
					</Anchor>
				</div>

				{#each fieldsToCompare as field}
					<div class="flex flex-col">
						<div class="text-sm font-medium text-surface-600-400">{safeTranslate(field.key)}</div>
						{#if field.format === 'markdown'}
							<div class="text-base text-surface-950-50">
								{#if data.compareAudit[field.key]}
									<MarkdownRenderer content={data.compareAudit[field.key]} />
								{:else}
									--
								{/if}
							</div>
						{:else}
							<div class="text-base font-semibold text-surface-950-50">
								{getFieldValue(data.compareAudit, field)}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- Maturity & Compliance Scores Comparison -->
	<div class="card bg-surface-50-950 shadow-lg">
		<div class="px-6 py-4 border-b border-surface-200-800">
			<h2 class="h4 font-bold">
				<i class="fa-solid fa-chart-line mr-2"></i>
				{m.scoresAndMetrics()}
			</h2>
		</div>
		<div class="grid grid-cols-2 divide-x divide-surface-200-800">
			<!-- Left: Base Audit Scores -->
			<div class="p-6">
				<div class="flex flex-col items-center space-y-4">
					<div class="flex flex-col items-center w-full h-48">
						{#if data.baseAudit && data.baseAudit.global_score >= 0}
							<RingProgress
								name="base_maturity"
								value={data.baseAudit.global_score}
								max={data.baseAudit.total_max_score}
								color={getScoreHexColor(
									data.baseAudit.global_score,
									data.baseAudit.total_max_score
								)}
								strokeWidth={32}
								fontSize={32}
								title={m.maturity()}
							/>
						{:else}
							<span class="text-sm font-medium text-surface-400-600 mb-2">{m.maturity()}</span>
							<div class="flex items-center justify-center size-40">
								<p class="text-surface-400-600 text-sm text-center">--</p>
							</div>
						{/if}
					</div>

					<div class="w-full flex flex-col gap-4 mt-4">
						<div class="w-full h-64">
							<DonutChart
								s_label={m.result()}
								name="base_compliance_result"
								title={m.compliance()}
								orientation="horizontal"
								height="h-full"
								values={data.baseAudit.donut_data.result.values}
								colors={data.baseAudit.donut_data.result.values.map(
									(object) => object.itemStyle.color
								)}
							/>
						</div>
						<div class="w-full h-64">
							<DonutChart
								s_label={m.status()}
								name="base_compliance_status"
								title={m.progress()}
								orientation="horizontal"
								height="h-full"
								values={data.baseAudit.donut_data.status.values}
								colors={data.baseAudit.donut_data.status.values.map(
									(object) => object.itemStyle.color
								)}
							/>
						</div>
					</div>
				</div>
			</div>

			<!-- Right: Comparison Audit Scores -->
			<div class="p-6">
				<div class="flex flex-col items-center space-y-4">
					<div class="flex flex-col items-center w-full h-48">
						{#if data.compareAudit && data.compareAudit.global_score >= 0}
							<RingProgress
								name="compare_maturity"
								value={data.compareAudit.global_score}
								max={data.compareAudit.total_max_score}
								color={getScoreHexColor(
									data.compareAudit.global_score,
									data.compareAudit.total_max_score
								)}
								strokeWidth={32}
								fontSize={32}
								title={m.maturity()}
							/>
						{:else}
							<span class="text-sm font-medium text-surface-400-600 mb-2">{m.maturity()}</span>
							<div class="flex items-center justify-center size-40">
								<p class="text-surface-400-600 text-sm text-center">--</p>
							</div>
						{/if}
					</div>

					<div class="w-full flex flex-col gap-4 mt-4">
						<div class="w-full h-64">
							<DonutChart
								s_label={m.result()}
								name="compare_compliance_result"
								title={m.compliance()}
								orientation="horizontal"
								height="h-full"
								values={data.compareAudit.donut_data.result.values}
								colors={data.compareAudit.donut_data.result.values.map(
									(object) => object.itemStyle.color
								)}
							/>
						</div>
						<div class="w-full h-64">
							<DonutChart
								s_label={m.status()}
								name="compare_compliance_status"
								title={m.progress()}
								orientation="horizontal"
								height="h-full"
								values={data.compareAudit.donut_data.status.values}
								colors={data.compareAudit.donut_data.status.values.map(
									(object) => object.itemStyle.color
								)}
							/>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Radar Charts Comparison -->
	<div class="card bg-surface-50-950 shadow-lg">
		<div class="px-6 py-4 border-b border-surface-200-800">
			<h2 class="h4 font-bold">
				<i class="fa-solid fa-chart-radar mr-2"></i>
				{m.radarComparisonByTopLevel()}
			</h2>
		</div>
		<div class="grid grid-cols-2 gap-6 p-6">
			<!-- Compliance Radar -->
			<div class="flex flex-col">
				<div class="h-96">
					<ComparisonRadarChart
						name="compliance_radar"
						title={m.compliance()}
						labels={data.baseAudit.radar_data.labels}
						baseData={data.baseAudit.radar_data.compliance_percentages}
						compareData={data.compareAudit.radar_data.compliance_percentages}
						baseName={data.baseAudit.name}
						compareName={data.compareAudit.name}
						height="h-full"
					/>
				</div>
				<p class="text-xs text-surface-600-400 text-center mt-2">
					<i class="fa-solid fa-info-circle mr-1"></i>
					{m.complianceIncludesCompliantAndPartiallyCompliant()}
				</p>
			</div>

			<!-- Maturity Radar -->
			<div class="h-96">
				<ComparisonRadarChart
					name="maturity_radar"
					title={m.maturity()}
					labels={data.baseAudit.radar_data.labels}
					baseData={data.baseAudit.radar_data.maturity_scores}
					compareData={data.compareAudit.radar_data.maturity_scores}
					baseName={data.baseAudit.name}
					compareName={data.compareAudit.name}
					maxValue={data.baseAudit.max_score || 100}
					height="h-full"
				/>
			</div>
		</div>
	</div>

	<!-- Differences Table -->
	{#if data.differences && data.differences.length > 0}
		<div class="card bg-surface-50-950 shadow-lg">
			<div class="px-6 py-4 border-b border-surface-200-800">
				<h2 class="h4 font-bold">
					<i class="fa-solid fa-code-compare mr-2"></i>
					{m.requirementDifferences()}
				</h2>
				<p class="text-sm text-surface-600-400 mt-1">
					{data.differences.length}
					{data.differences.length === 1 ? m.requirement() : m.requirements()}
					{m.withDifferences()}
				</p>
			</div>
			<div class="overflow-x-auto">
				<table class="table-auto w-full">
					<thead>
						<tr class="bg-surface-50-950">
							<th
								class="px-6 py-3 text-left text-xs font-medium text-surface-700-300 uppercase tracking-wider"
							>
								{m.requirement()}
							</th>
							<th
								class="px-6 py-3 text-left text-xs font-medium text-surface-700-300 uppercase tracking-wider"
							>
								{m.baseAudit()}
							</th>
							<th
								class="px-6 py-3 text-left text-xs font-medium text-surface-700-300 uppercase tracking-wider"
							>
								{m.comparisonAudit()}
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-surface-200-800">
						{#each data.differences as diff}
							<tr class="hover:bg-surface-50-950">
								<td class="px-6 py-4">
									<div class="flex flex-col">
										{#if diff.requirement.ref_id}
											<span class="font-semibold text-sm">{diff.requirement.ref_id}</span>
										{/if}
										{#if diff.requirement.name}
											<span class="text-sm text-surface-950-50">{diff.requirement.name}</span>
										{/if}
									</div>
								</td>
								<td class="px-6 py-4">
									<div class="flex flex-col space-y-1">
										<div class="flex items-center space-x-2">
											<span class="text-xs text-surface-600-400">{m.result()}:</span>
											<span
												class="badge text-xs"
												style="background-color: {diff.base.result === 'compliant'
													? '#86efac'
													: diff.base.result === 'partially_compliant'
														? '#fde047'
														: diff.base.result === 'non_compliant'
															? '#f87171'
															: diff.base.result === 'not_applicable'
																? '#000000'
																: '#d1d5db'}; color: {diff.base.result === 'not_applicable'
													? 'white'
													: 'black'};"
											>
												{safeTranslate(diff.base.result)}
											</span>
										</div>
										{#if diff.base.score !== null && diff.base.score !== undefined}
											<div class="flex items-center space-x-2">
												<span class="text-xs text-surface-600-400">{m.score()}:</span>
												<span class="text-xs font-medium">{diff.base.score}</span>
											</div>
										{/if}
									</div>
								</td>
								<td class="px-6 py-4">
									<div class="flex flex-col space-y-1">
										<div class="flex items-center space-x-2">
											<span class="text-xs text-surface-600-400">{m.result()}:</span>
											<span
												class="badge text-xs"
												style="background-color: {diff.compare.result === 'compliant'
													? '#86efac'
													: diff.compare.result === 'partially_compliant'
														? '#fde047'
														: diff.compare.result === 'non_compliant'
															? '#f87171'
															: diff.compare.result === 'not_applicable'
																? '#000000'
																: '#d1d5db'}; color: {diff.compare.result === 'not_applicable'
													? 'white'
													: 'black'};"
											>
												{safeTranslate(diff.compare.result)}
											</span>
										</div>
										{#if diff.compare.score !== null && diff.compare.score !== undefined}
											<div class="flex items-center space-x-2">
												<span class="text-xs text-surface-600-400">{m.score()}:</span>
												<span class="text-xs font-medium">{diff.compare.score}</span>
											</div>
										{/if}
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
