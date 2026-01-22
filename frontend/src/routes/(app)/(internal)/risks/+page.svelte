<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: breadcrumbs = [
		{ label: 'Risk Management Dashboard', href: `${base}/risks` }
	];
</script>

<svelte:head>
	<title>{data.title}</title>
</svelte:head>

<Breadcrumbs items={breadcrumbs} />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
			Risk Management Dashboard
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Enterprise risk assessment and management overview
		</p>
	</div>

	<!-- Key Risk Metrics -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
		<!-- Total Asset Risks -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-red-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Asset Risks</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalAssetRisks}</p>
						<div class="flex items-center text-sm">
							<span class="text-red-600 font-medium">{data.metrics.overallRiskLevel}% high/critical</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/risks/asset-risks`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View all risks →
					</a>
				</div>
			</div>
		</div>

		<!-- Critical Risks -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-red-600 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Critical Risks</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.criticalRisks}</p>
						<div class="flex items-center text-sm">
							<span class="text-red-600 font-medium">Requires immediate attention</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/risks/asset-risks?risk_level=critical`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View critical risks →
					</a>
				</div>
			</div>
		</div>

		<!-- Risk Registers -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-blue-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Risk Registers</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalRiskRegisters}</p>
						<div class="flex items-center text-sm">
							<span class="text-blue-600 font-medium">{data.metrics.activeRegisters} active</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/risks/risk-registers`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						Manage registers →
					</a>
				</div>
			</div>
		</div>

		<!-- Risk Heat Map -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-yellow-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Risk Heat Map</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">
							{data.metrics.riskScoreDistribution.very_high + data.metrics.riskScoreDistribution.high}
						</p>
						<div class="flex items-center text-sm">
							<span class="text-yellow-600 font-medium">High risk items</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/analytics/risks`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View heat map →
					</a>
				</div>
			</div>
		</div>
	</div>

	<!-- Risk Distribution Chart -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Risk Distribution</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-5 gap-4">
				<div class="text-center">
					<div class="text-2xl font-bold text-red-600">{data.metrics.riskScoreDistribution.very_high}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Very High (8-10)</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-orange-600">{data.metrics.riskScoreDistribution.high}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">High (6-8)</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-yellow-600">{data.metrics.riskScoreDistribution.medium}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Medium (4-6)</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-blue-600">{data.metrics.riskScoreDistribution.low}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Low (2-4)</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-green-600">{data.metrics.riskScoreDistribution.very_low}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Very Low (0-2)</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Quick Actions -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Quick Actions</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<a
					href={`${base}/risks/asset-risks/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">New Asset Risk</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Identify and assess new risks</p>
					</div>
				</a>

				<a
					href={`${base}/risks/risk-registers/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Create Risk Register</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Organize risks by category</p>
					</div>
				</a>

				<a
					href={`${base}/analytics/risks`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Risk Analytics</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">View risk heat maps and trends</p>
					</div>
				</a>

				<a
					href={`${base}/risks/risk-matrix`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Risk Matrix</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Configure risk assessment matrix</p>
					</div>
				</a>
			</div>
		</div>
	</div>

	<!-- Recent Risk Activity -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
		<!-- Recent Asset Risks -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent Asset Risks</h3>
			</div>
			<div class="p-6">
				{#if data.recentRisks.length > 0}
					<div class="space-y-4">
						{#each data.recentRisks as risk}
							<div class="flex items-center justify-between">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class={`h-8 w-8 rounded-full flex items-center justify-center ${
											risk.risk_level === 'critical' ? 'bg-red-500' :
											risk.risk_level === 'high' ? 'bg-orange-500' :
											risk.risk_level === 'medium' ? 'bg-yellow-500' :
											'bg-green-500'
										}`}>
											<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{risk.risk_title}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											Score: {risk.calculated_risk_score}/10
										</p>
									</div>
								</div>
								<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
									risk.risk_level === 'critical' ? 'bg-red-100 text-red-800' :
									risk.risk_level === 'high' ? 'bg-orange-100 text-orange-800' :
									risk.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
									'bg-green-100 text-green-800'
								}`}>
									{risk.risk_level}
								</span>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No asset risks identified yet.</p>
				{/if}
			</div>
		</div>

		<!-- Risk Registers -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Risk Registers</h3>
			</div>
			<div class="p-6">
				{#if data.riskRegisters.length > 0}
					<div class="space-y-4">
						{#each data.riskRegisters as register}
							<div class="flex items-center justify-between">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center">
											<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{register.name}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											{register.risk_count || 0} risks
										</p>
									</div>
								</div>
								<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
									register.status === 'active' ? 'bg-green-100 text-green-800' :
									'bg-gray-100 text-gray-800'
								}`}>
									{register.status}
								</span>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No risk registers created yet.</p>
				{/if}
			</div>
		</div>
	</div>
</div>
