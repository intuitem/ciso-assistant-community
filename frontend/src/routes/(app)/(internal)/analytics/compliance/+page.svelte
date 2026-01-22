<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: breadcrumbs = [
		{ label: 'Analytics', href: `${base}/analytics` },
		{ label: 'Compliance Analytics', href: `${base}/analytics/compliance` }
	];

	const getStatusColor = (status: string) => {
		const colors = {
			'compliant': 'bg-green-100 text-green-800',
			'partial': 'bg-yellow-100 text-yellow-800',
			'non-compliant': 'bg-red-100 text-red-800'
		};
		return colors[status] || 'bg-gray-100 text-gray-800';
	};

	const getScoreColor = (score: number) => {
		if (score >= 80) return 'text-green-600';
		if (score >= 60) return 'text-yellow-600';
		return 'text-red-600';
	};
</script>

<svelte:head>
	<title>{data.title}</title>
</svelte:head>

<Breadcrumbs items={breadcrumbs} />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
			Compliance Analytics Dashboard
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Comprehensive compliance assessment results and framework performance
		</p>
	</div>

	<!-- Key Compliance Metrics -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
		<!-- Overall Compliance Score -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-blue-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Overall Compliance</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.avgComplianceScore}%</p>
						<div class="flex items-center text-sm">
							<span class={`font-medium ${getScoreColor(data.analytics.avgComplianceScore)}`}>
								{data.analytics.avgComplianceScore >= 80 ? 'Strong' :
								 data.analytics.avgComplianceScore >= 60 ? 'Moderate' : 'Needs Attention'}
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Total Assessments -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-green-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Assessments</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.totalAssessments}</p>
						<div class="flex items-center text-sm">
							<span class="text-green-600 font-medium">{data.analytics.completedAssessments} completed</span>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Findings & Exceptions -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-yellow-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Open Issues</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.findingsCount + data.analytics.exceptionsCount}</p>
						<div class="flex items-center text-sm">
							<span class="text-yellow-600 font-medium">{data.analytics.findingsCount} findings</span>
							<span class="text-gray-400 mx-2">•</span>
							<span class="text-orange-600 font-medium">{data.analytics.exceptionsCount} exceptions</span>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Frameworks Covered -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-purple-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Frameworks</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{Object.keys(data.analytics.frameworkStats).length}</p>
						<div class="flex items-center text-sm">
							<span class="text-green-600 font-medium">{data.analytics.compliantFrameworks.length} compliant</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Framework Compliance Overview -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Framework Compliance Overview</h3>
			<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Compliance scores and status by regulatory framework</p>
		</div>
		<div class="p-6">
			<div class="space-y-4">
				{#each data.analytics.complianceByFramework as framework}
					<div class="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-600 rounded-lg">
						<div class="flex-1">
							<div class="flex items-center justify-between mb-2">
								<h4 class="text-sm font-medium text-gray-900 dark:text-white">{framework.framework}</h4>
								<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(framework.status)}`}>
									{framework.status}
								</span>
							</div>
							<div class="flex items-center justify-between">
								<div class="flex items-center text-sm text-gray-500 dark:text-gray-400">
									<span>{framework.assessments} assessments</span>
								</div>
								<div class="flex items-center">
									<span class={`text-lg font-semibold mr-2 ${getScoreColor(framework.score)}`}>
										{framework.score}%
									</span>
									<div class="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div
											class="bg-blue-600 h-2 rounded-full transition-all duration-300"
											style="width: {framework.score}%"
										></div>
									</div>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- Assessment Status Distribution -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Assessment Status Distribution</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="text-center">
					<div class="text-3xl font-bold text-green-600 mb-2">{data.analytics.completedAssessments}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Completed</div>
					<div class="mt-1 text-xs text-green-600">Assessments finalized</div>
				</div>
				<div class="text-center">
					<div class="text-3xl font-bold text-blue-600 mb-2">{data.analytics.inProgressAssessments}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">In Progress</div>
					<div class="mt-1 text-xs text-blue-600">Currently active</div>
				</div>
				<div class="text-center">
					<div class="text-3xl font-bold text-gray-600 mb-2">{data.analytics.plannedAssessments}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Planned</div>
					<div class="mt-1 text-xs text-gray-600">Scheduled for future</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Recent Assessments -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent Compliance Assessments</h3>
		</div>
		<div class="p-6">
			{#if data.analytics.recentAssessments.length > 0}
				<div class="space-y-4">
					{#each data.analytics.recentAssessments as assessment}
						<div class="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-600 rounded-lg">
							<div class="flex items-center">
								<div class="flex-shrink-0">
									<div class={`h-8 w-8 rounded-full flex items-center justify-center ${
										assessment.status === 'completed' ? 'bg-green-500' :
										assessment.status === 'in_progress' ? 'bg-blue-500' :
										'bg-gray-500'
									}`}>
										<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
										</svg>
									</div>
								</div>
								<div class="ml-3">
									<p class="text-sm font-medium text-gray-900 dark:text-white">
										{assessment.primary_framework} Assessment
									</p>
									<p class="text-sm text-gray-500 dark:text-gray-400">
										Status: {assessment.status} • Score: {assessment.overall_compliance_score || 'N/A'}%
									</p>
								</div>
							</div>
							<div class="flex items-center">
								{#if assessment.status === 'completed' && assessment.overall_compliance_score}
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-3 ${getStatusColor(
										assessment.overall_compliance_score >= 80 ? 'compliant' :
										assessment.overall_compliance_score >= 60 ? 'partial' : 'non-compliant'
									)}`}>
										{assessment.overall_compliance_score >= 80 ? 'Compliant' :
										 assessment.overall_compliance_score >= 60 ? 'Partial' : 'Non-Compliant'}
									</span>
								{/if}
								<a
									href={`${base}/compliance/assessments/${assessment.id}`}
									class="text-blue-600 hover:text-blue-500 text-sm font-medium"
								>
									View Details →
								</a>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-sm text-gray-500 dark:text-gray-400">No compliance assessments found.</p>
			{/if}
		</div>
	</div>

	<!-- Action Items -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Compliance Actions</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				<a
					href={`${base}/compliance/assessments/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">New Assessment</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Start compliance evaluation</p>
					</div>
				</a>

				<a
					href={`${base}/compliance/frameworks`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Framework Library</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Browse compliance frameworks</p>
					</div>
				</a>

				<a
					href={`${base}/reports/compliance`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Compliance Reports</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Generate compliance reports</p>
					</div>
				</a>
			</div>
		</div>
	</div>
</div>
