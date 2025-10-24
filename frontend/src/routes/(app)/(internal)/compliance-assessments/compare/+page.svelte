<script lang="ts">
	import { page } from '$app/state';
	import type { PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import { displayScoreColor } from '$lib/utils/helpers';
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

		if (value.str) return value.str;

		return safeTranslate(value);
	}
</script>

<div class="flex flex-col space-y-4">
	<div class="card p-4 bg-white shadow-lg">
		<div class="flex items-center justify-between mb-4">
			<div class="flex flex-col">
				<h1 class="h2 font-bold">
					<i class="fa-solid fa-code-compare mr-2"></i>
					{m.complianceAssessmentComparison()}
				</h1>
				<div class="text-sm text-gray-600 mt-1">
					<span class="font-medium">{m.framework()}:</span>
					{data.framework.str}
				</div>
			</div>
			<Anchor
				href="/compliance-assessments/{data.baseAudit.id}"
				class="btn preset-filled-surface-500"
			>
				<i class="fa-solid fa-arrow-left mr-2"></i>
				{m.backToBaseAudit()}
			</Anchor>
		</div>
	</div>

	<div class="card bg-white shadow-lg">
		<div class="grid grid-cols-2 divide-x divide-gray-200">
			<!-- Left side: Base Audit -->
			<div class="p-6 space-y-4">
				<div class="flex items-center justify-between mb-4">
					<h2 class="h3 font-bold text-primary-500">{m.baseAudit()}</h2>
					<Anchor
						href="/compliance-assessments/{data.baseAudit.id}"
						class="btn btn-sm preset-filled-primary-500"
					>
						<i class="fa-solid fa-external-link-alt mr-2"></i>
						{m.view()}
					</Anchor>
				</div>

				{#each fieldsToCompare as field}
					<div class="flex flex-col">
						<div class="text-sm font-medium text-gray-600">{safeTranslate(field.key)}</div>
						{#if field.format === 'markdown'}
							<div class="text-base text-gray-900">
								{#if data.baseAudit[field.key]}
									<MarkdownRenderer content={data.baseAudit[field.key]} />
								{:else}
									--
								{/if}
							</div>
						{:else}
							<div class="text-base font-semibold text-gray-900">
								{getFieldValue(data.baseAudit, field)}
							</div>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Right side: Comparison Audit -->
			<div class="p-6 space-y-4">
				<div class="flex items-center justify-between mb-4">
					<h2 class="h3 font-bold text-secondary-500">{m.comparisonAudit()}</h2>
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
						<div class="text-sm font-medium text-gray-600">{safeTranslate(field.key)}</div>
						{#if field.format === 'markdown'}
							<div class="text-base text-gray-900">
								{#if data.compareAudit[field.key]}
									<MarkdownRenderer content={data.compareAudit[field.key]} />
								{:else}
									--
								{/if}
							</div>
						{:else}
							<div class="text-base font-semibold text-gray-900">
								{getFieldValue(data.compareAudit, field)}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- Maturity & Compliance Scores Comparison -->
	<div class="card bg-white shadow-lg">
		<div class="px-6 py-4 border-b border-gray-200">
			<h2 class="h3 font-bold">
				<i class="fa-solid fa-chart-line mr-2"></i>
				{m.scoresAndMetrics()}
			</h2>
		</div>
		<div class="grid grid-cols-2 divide-x divide-gray-200">
			<!-- Left: Base Audit Scores -->
			<div class="p-6">
				<div class="flex flex-col items-center space-y-4">
					{#if data.baseAudit.global_score >= 0}
						<div class="flex flex-col items-center">
							<span class="text-sm font-medium text-gray-600 mb-2">{m.maturity()}</span>
							<ProgressRing
								strokeWidth="20px"
								meterStroke={displayScoreColor(
									data.baseAudit.global_score,
									data.baseAudit.max_score
								)}
								value={(data.baseAudit.global_score * 100) / data.baseAudit.max_score}
								size="size-40"
							>
								<p class="font-semibold text-3xl">{data.baseAudit.global_score}</p>
							</ProgressRing>
						</div>
					{/if}

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
					{#if data.compareAudit.global_score >= 0}
						<div class="flex flex-col items-center">
							<span class="text-sm font-medium text-gray-600 mb-2">{m.maturity()}</span>
							<ProgressRing
								strokeWidth="20px"
								meterStroke={displayScoreColor(
									data.compareAudit.global_score,
									data.compareAudit.max_score
								)}
								value={(data.compareAudit.global_score * 100) / data.compareAudit.max_score}
								size="size-40"
							>
								<p class="font-semibold text-3xl">{data.compareAudit.global_score}</p>
							</ProgressRing>
						</div>
					{/if}

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
	<div class="card bg-white shadow-lg">
		<div class="px-6 py-4 border-b border-gray-200">
			<h2 class="h3 font-bold">
				<i class="fa-solid fa-chart-radar mr-2"></i>
				{m.radarComparisonByTopLevel()}
			</h2>
		</div>
		<div class="grid grid-cols-2 gap-6 p-6">
			<!-- Compliance Radar -->
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
					height="h-full"
				/>
			</div>
		</div>
	</div>

	<div class="card p-6 bg-white shadow-lg">
		<div class="flex items-center justify-center text-gray-500 py-8">
			<div class="text-center space-y-2">
				<i class="fa-solid fa-tools text-4xl"></i>
				<p class="text-lg font-medium">{m.moreComparisonFeaturesComingSoon()}</p>
				<p class="text-sm">
					{m.futureComparisonFeatures()}
				</p>
			</div>
		</div>
	</div>
</div>
