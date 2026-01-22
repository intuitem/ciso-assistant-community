<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: breadcrumbs = [
		{ label: 'Business Continuity Management', href: `${base}/business-continuity` }
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
			Business Continuity Management
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Comprehensive business continuity planning and disaster recovery
		</p>
	</div>

	<!-- Critical Alerts Banner -->
	{#if data.metrics.plansNeedingAttention.length > 0}
		<div class="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 p-4 mb-6">
			<div class="flex">
				<div class="flex-shrink-0">
					<svg class="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
					</svg>
				</div>
				<div class="ml-3">
					<h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
						Business Continuity Plans Need Attention
					</h3>
					<div class="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
						<p>{data.metrics.plansNeedingAttention.length} BCP plans require updates, testing, or review.</p>
					</div>
					<div class="mt-4">
						<div class="-mx-2 -my-1.5 flex">
							<a
								href={`${base}/business-continuity/plans?status=needs_attention`}
								class="bg-yellow-50 dark:bg-yellow-900/20 px-2 py-1.5 rounded-md text-sm font-medium text-yellow-800 dark:text-yellow-200 hover:bg-yellow-100 dark:hover:bg-yellow-800/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-yellow-50 focus:ring-yellow-600"
							>
								Review Plans →
							</a>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Key BCP Metrics -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
		<!-- Total BCP Plans -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total BCP Plans</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalPlans}</p>
						<div class="flex items-center text-sm">
							<span class="text-blue-600 font-medium">{data.metrics.activePlans} active</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/business-continuity/plans`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View all plans →
					</a>
				</div>
			</div>
		</div>

		<!-- Plans Up to Date -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-green-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Plans Up to Date</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.plansUpToDate}%</p>
						<div class="flex items-center text-sm">
							<span class="text-green-600 font-medium">{data.metrics.plansTestedThisYear} tested this year</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/analytics/business-continuity`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View testing status →
					</a>
				</div>
			</div>
		</div>

		<!-- Test Success Rate -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Test Success Rate</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.testSuccessRate}%</p>
						<div class="flex items-center text-sm">
							<span class={`font-medium ${data.metrics.testSuccessRate >= 80 ? 'text-green-600' : data.metrics.testSuccessRate >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
								{data.metrics.testSuccessRate >= 80 ? 'Excellent' : data.metrics.testSuccessRate >= 60 ? 'Good' : 'Needs Improvement'}
							</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/business-continuity/tests`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View test results →
					</a>
				</div>
			</div>
		</div>

		<!-- High Impact Plans -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-red-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">High Impact Plans</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.highImpactPlans}</p>
						<div class="flex items-center text-sm">
							<span class="text-red-600 font-medium">Critical business functions</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/business-continuity/plans?impact=high`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View critical plans →
					</a>
				</div>
			</div>
		</div>
	</div>

	<!-- BCP Status Overview -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">BCP Status Overview</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				<div class="text-center">
					<div class="text-3xl font-bold text-green-600">{data.metrics.activePlans}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Active Plans</div>
					<div class="mt-2 text-xs text-green-600">Ready for execution</div>
				</div>
				<div class="text-center">
					<div class="text-3xl font-bold text-yellow-600">{data.metrics.draftPlans}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Draft Plans</div>
					<div class="mt-2 text-xs text-yellow-600">Under development</div>
				</div>
				<div class="text-center">
					<div class="text-3xl font-bold text-red-600">{data.metrics.expiredPlans}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Expired Plans</div>
					<div class="mt-2 text-xs text-red-600">Require immediate update</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Quick Actions -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Business Continuity Actions</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<a
					href={`${base}/business-continuity/plans/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Create BCP Plan</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Develop new business continuity plan</p>
					</div>
				</a>

				<a
					href={`${base}/business-continuity/tests/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Schedule BCP Test</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Plan and execute continuity testing</p>
					</div>
				</a>

				<a
					href={`${base}/business-continuity/incidents/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Report Incident</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Activate business continuity procedures</p>
					</div>
				</a>

				<a
					href={`${base}/analytics/business-continuity`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">BCP Analytics</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Business continuity dashboards and reports</p>
					</div>
				</a>
			</div>
		</div>
	</div>

	<!-- Recent Activity -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
		<!-- Recent BCP Plans -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent BCP Plans</h3>
			</div>
			<div class="p-6">
				{#if data.metrics.recentPlans.length > 0}
					<div class="space-y-4">
						{#each data.metrics.recentPlans as plan}
							<div class="flex items-center justify-between">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class={`h-8 w-8 rounded-full flex items-center justify-center ${
											plan.business_impact === 'high' ? 'bg-red-500' :
											plan.business_impact === 'medium' ? 'bg-yellow-500' :
											'bg-green-500'
										}`}>
											<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{plan.plan_name}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											Last tested: {plan.last_test_date ? new Date(plan.last_test_date).toLocaleDateString() : 'Never tested'}
										</p>
									</div>
								</div>
								<div class="flex flex-col items-end">
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mb-1 ${
										plan.business_impact === 'high' ? 'bg-red-100 text-red-800' :
										plan.business_impact === 'medium' ? 'bg-yellow-100 text-yellow-800' :
										'bg-green-100 text-green-800'
									}`}>
										{plan.business_impact} impact
									</span>
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
										plan.status === 'active' ? 'bg-green-100 text-green-800' :
										plan.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
										'bg-red-100 text-red-800'
									}`}>
										{plan.status}
									</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No BCP plans created yet.</p>
				{/if}
			</div>
		</div>

		<!-- Plans Needing Attention -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Plans Needing Attention</h3>
			</div>
			<div class="p-6">
				{#if data.metrics.plansNeedingAttention.length > 0}
					<div class="space-y-4">
						{#each data.metrics.plansNeedingAttention as plan}
							<div class="border border-yellow-200 dark:border-yellow-700 rounded-lg p-4 bg-yellow-50 dark:bg-yellow-900/20">
								<div class="flex items-center justify-between">
									<div class="flex items-center">
										<div class="flex-shrink-0">
											<div class="h-8 w-8 rounded-full bg-yellow-500 flex items-center justify-center">
												<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
												</svg>
											</div>
										</div>
										<div class="ml-3">
											<p class="text-sm font-medium text-yellow-900 dark:text-yellow-200 truncate">
												{plan.plan_name}
											</p>
											<p class="text-sm text-yellow-700 dark:text-yellow-300">
												{#if plan.status === 'expired'}
													Plan has expired and needs update
												{:else if !plan.last_test_date || new Date(plan.last_test_date) < new Date(Date.now() - 365 * 24 * 60 * 60 * 1000)}
													Annual testing overdue
												{:else if plan.last_test_result === 'failed'}
													Last test failed - requires review
												{/if}
											</p>
										</div>
									</div>
									<div class="flex flex-col items-end">
										<a
											href={`${base}/business-continuity/plans/${plan.id}`}
											class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-yellow-700 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 dark:bg-yellow-800 dark:text-yellow-200 dark:hover:bg-yellow-700"
										>
											Review
										</a>
									</div>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-center py-6">
						<svg class="mx-auto h-12 w-12 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
						<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">All Plans Current</h3>
						<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">All BCP plans are up to date and tested.</p>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
