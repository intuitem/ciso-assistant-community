<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: breadcrumbs = [
		{ label: 'Executive GRC Analytics Dashboard', href: `${base}/analytics` }
	];

	// Helper functions for styling
	const getHealthColor = (score: number) => {
		if (score >= 80) return 'text-green-600 bg-green-100';
		if (score >= 60) return 'text-yellow-600 bg-yellow-100';
		return 'text-red-600 bg-red-100';
	};

	const getMaturityColor = (level: string) => {
		const colors = {
			'advanced': 'bg-green-100 text-green-800',
			'mature': 'bg-blue-100 text-blue-800',
			'developing': 'bg-yellow-100 text-yellow-800',
			'emerging': 'bg-orange-100 text-orange-800',
			'initial': 'bg-red-100 text-red-800'
		};
		return colors[level] || 'bg-gray-100 text-gray-800';
	};

	const getTrendIcon = (trend: string) => {
		switch (trend) {
			case 'increasing':
			case 'improving':
				return '↗️';
			case 'decreasing':
				return '↘️';
			default:
				return '→';
		}
	};

	const getSeverityColor = (severity: string) => {
		const colors = {
			'critical': 'bg-red-100 text-red-800',
			'high': 'bg-orange-100 text-orange-800',
			'medium': 'bg-yellow-100 text-yellow-800',
			'low': 'bg-green-100 text-green-800'
		};
		return colors[severity] || 'bg-gray-100 text-gray-800';
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
			Executive GRC Analytics Dashboard
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Comprehensive governance, risk, and compliance insights across all domains
		</p>
	</div>

	<!-- GRC Health Score - Hero Section -->
	<div class="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-lg mb-8">
		<div class="px-6 py-8 sm:px-8">
			<div class="flex items-center justify-between">
				<div>
					<h2 class="text-2xl font-bold text-white">GRC Health Score</h2>
					<p class="mt-1 text-blue-100">Overall organizational risk and compliance posture</p>
				</div>
				<div class="text-right">
					<div class="text-6xl font-bold text-white">{data.analytics.grcHealthScore}</div>
					<div class="text-blue-100 text-sm">out of 100</div>
				</div>
			</div>
			<div class="mt-6">
				<div class="flex items-center">
					<div class="flex-1 bg-blue-200 rounded-full h-3">
						<div
							class="bg-white rounded-full h-3 transition-all duration-500"
							style="width: {data.analytics.grcHealthScore}%"
						></div>
					</div>
					<span class="ml-4 text-white font-medium">
						{data.analytics.grcHealthScore >= 80 ? 'Excellent' :
						 data.analytics.grcHealthScore >= 60 ? 'Good' :
						 data.analytics.grcHealthScore >= 40 ? 'Needs Attention' : 'Critical'}
					</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Domain Overview Cards -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
		<!-- Privacy & Data Protection -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white">Privacy & Data Protection</h3>
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMaturityColor(data.analytics.maturityLevels.privacy)}`}>
						{data.analytics.maturityLevels.privacy}
					</span>
				</div>
			</div>
			<div class="p-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Data Assets</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.privacy.totalDataAssets}</p>
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Compliance Rate</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.privacy.avgComplianceRate}%</p>
					</div>
				</div>
				<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
					<div class="flex items-center text-sm">
						<span class="text-gray-500 dark:text-gray-400">Trend:</span>
						<span class="ml-2 font-medium text-green-600">{getTrendIcon(data.analytics.trends.privacyTrend)} Improving</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Enterprise Risk Management -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white">Enterprise Risk</h3>
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMaturityColor(data.analytics.maturityLevels.risk)}`}>
						{data.analytics.maturityLevels.risk}
					</span>
				</div>
			</div>
			<div class="p-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Risks</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.risk.totalRisks}</p>
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Critical Risks</p>
						<p class="text-2xl font-semibold text-red-600">{data.analytics.risk.criticalRisks}</p>
					</div>
				</div>
				<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
					<div class="flex items-center text-sm">
						<span class="text-gray-500 dark:text-gray-400">Trend:</span>
						<span class="ml-2 font-medium text-green-600">{getTrendIcon(data.analytics.trends.riskTrend)} Decreasing</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Security Operations -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white">Security Operations</h3>
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMaturityColor(data.analytics.maturityLevels.security)}`}>
						{data.analytics.maturityLevels.security}
					</span>
				</div>
			</div>
			<div class="p-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Incidents</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.security.totalIncidents}</p>
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Active Incidents</p>
						<p class="text-2xl font-semibold text-orange-600">{data.analytics.security.activeIncidents}</p>
					</div>
				</div>
				<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
					<div class="flex items-center text-sm">
						<span class="text-gray-500 dark:text-gray-400">Trend:</span>
						<span class="ml-2 font-medium text-blue-600">{getTrendIcon(data.analytics.trends.incidentTrend)} Stable</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Third Party Risk -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white">Third Party Risk</h3>
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMaturityColor(data.analytics.maturityLevels.thirdParty)}`}>
						{data.analytics.maturityLevels.thirdParty}
					</span>
				</div>
			</div>
			<div class="p-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Entities</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.thirdParty.totalEntities}</p>
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">High Risk</p>
						<p class="text-2xl font-semibold text-red-600">{data.analytics.thirdParty.highRiskEntities}</p>
					</div>
				</div>
				<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
					<div class="flex items-center text-sm">
						<span class="text-gray-500 dark:text-gray-400">Contract Health:</span>
						<span class="ml-2 font-medium text-green-600">{data.analytics.thirdParty.complianceRate}%</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Compliance Management -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white">Compliance</h3>
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMaturityColor(data.analytics.maturityLevels.compliance)}`}>
						{data.analytics.maturityLevels.compliance}
					</span>
				</div>
			</div>
			<div class="p-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Assessments</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.compliance.totalAssessments}</p>
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Completed</p>
						<p class="text-2xl font-semibold text-green-600">{data.analytics.compliance.completedAssessments}</p>
					</div>
				</div>
				<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
					<div class="flex items-center text-sm">
						<span class="text-gray-500 dark:text-gray-400">Trend:</span>
						<span class="ml-2 font-medium text-green-600">{getTrendIcon(data.analytics.trends.complianceTrend)} Increasing</span>
					</div>
				</div>
			</div>
		</div>

		<!-- Business Continuity -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white">Business Continuity</h3>
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getMaturityColor(data.analytics.maturityLevels.businessContinuity)}`}>
						{data.analytics.maturityLevels.businessContinuity}
					</span>
				</div>
			</div>
			<div class="p-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">BCP Plans</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.analytics.businessContinuity.totalPlans}</p>
					</div>
					<div>
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Test Success</p>
						<p class="text-2xl font-semibold text-green-600">{data.analytics.businessContinuity.testSuccessRate}%</p>
					</div>
				</div>
				<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
					<div class="flex items-center text-sm">
						<span class="text-gray-500 dark:text-gray-400">Active Plans:</span>
						<span class="ml-2 font-medium text-blue-600">{data.analytics.businessContinuity.activePlans}</span>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Top Risks Across All Domains -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Top Enterprise Risks</h3>
			<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Aggregated risk analysis across all GRC domains</p>
		</div>
		<div class="p-6">
			<div class="space-y-4">
				{#each data.analytics.topRisks as risk}
					<div class="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-600 rounded-lg">
						<div class="flex items-center">
							<div class="flex-shrink-0">
								<div class={`h-3 w-3 rounded-full ${
									risk.severity === 'critical' ? 'bg-red-500' :
									risk.severity === 'high' ? 'bg-orange-500' :
									risk.severity === 'medium' ? 'bg-yellow-500' :
									'bg-green-500'
								}`}></div>
							</div>
							<div class="ml-4">
								<p class="text-sm font-medium text-gray-900 dark:text-white">{risk.category}</p>
								<p class="text-sm text-gray-500 dark:text-gray-400">Identified risk areas requiring attention</p>
							</div>
						</div>
						<div class="flex items-center">
							<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-3 ${getSeverityColor(risk.severity)}`}>
								{risk.severity}
							</span>
							<span class="text-sm font-medium text-gray-900 dark:text-white">{risk.count} issues</span>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- Key Performance Indicators -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Key Performance Indicators</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
				<div class="text-center">
					<div class="text-3xl font-bold text-blue-600 mb-2">{data.analytics.privacy.avgComplianceRate}%</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Privacy Compliance</div>
					<div class="mt-1 text-xs text-green-600">Target: 95%</div>
				</div>
				<div class="text-center">
					<div class="text-3xl font-bold text-green-600 mb-2">{data.analytics.thirdParty.complianceRate}%</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Contract Health</div>
					<div class="mt-1 text-xs text-green-600">Target: 90%</div>
				</div>
				<div class="text-center">
					<div class="text-3xl font-bold text-purple-600 mb-2">{data.analytics.businessContinuity.testSuccessRate}%</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">BCP Test Success</div>
					<div class="mt-1 text-xs text-green-600">Target: 100%</div>
				</div>
				<div class="text-center">
					<div class="text-3xl font-bold text-orange-600 mb-2">{data.analytics.grcHealthScore}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">GRC Health Score</div>
					<div class="mt-1 text-xs text-blue-600">Overall Health</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Quick Actions for Executives -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Executive Actions</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<a
					href={`${base}/analytics/risks`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Risk Heat Map</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">View enterprise risk landscape</p>
					</div>
				</a>

				<a
					href={`${base}/analytics/compliance`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Compliance Dashboard</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Framework compliance status</p>
					</div>
				</a>

				<a
					href={`${base}/reports/executive-summary`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Executive Report</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Generate comprehensive reports</p>
					</div>
				</a>

				<a
					href={`${base}/settings/governance`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Governance Settings</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Configure GRC policies</p>
					</div>
				</a>
			</div>
		</div>
	</div>
</div>