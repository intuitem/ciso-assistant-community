<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: breadcrumbs = [
		{ label: 'Third Party Risk Management', href: `${base}/third-party` }
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
			Third Party Risk Management
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Comprehensive vendor risk assessment and contract management
		</p>
	</div>

	<!-- Risk Alerts Banner -->
	{#if data.metrics.criticalRiskEntities > 0 || data.metrics.expiringContracts > 0}
		<div class="space-y-4 mb-6">
			{#if data.metrics.criticalRiskEntities > 0}
				<div class="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 p-4">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
							</svg>
						</div>
						<div class="ml-3">
							<h3 class="text-sm font-medium text-red-800 dark:text-red-200">
								Critical Risk Vendors Require Attention
							</h3>
							<div class="mt-2 text-sm text-red-700 dark:text-red-300">
								<p>{data.metrics.criticalRiskEntities} vendors have critical risk levels requiring immediate review.</p>
							</div>
							<div class="mt-4">
								<div class="-mx-2 -my-1.5 flex">
									<a
										href={`${base}/third-party/entities?risk_level=critical`}
										class="bg-red-50 dark:bg-red-900/20 px-2 py-1.5 rounded-md text-sm font-medium text-red-800 dark:text-red-200 hover:bg-red-100 dark:hover:bg-red-800/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
									>
										Review Critical Vendors →
									</a>
								</div>
							</div>
						</div>
					</div>
				</div>
			{/if}

			{#if data.metrics.expiringContracts > 0}
				<div class="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 p-4">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						</div>
						<div class="ml-3">
							<h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
								Contracts Expiring Soon
							</h3>
							<div class="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
								<p>{data.metrics.expiringContracts} contracts will expire within 90 days.</p>
							</div>
							<div class="mt-4">
								<div class="-mx-2 -my-1.5 flex">
									<a
										href={`${base}/third-party/entities?contract_status=expiring_soon`}
										class="bg-yellow-50 dark:bg-yellow-900/20 px-2 py-1.5 rounded-md text-sm font-medium text-yellow-800 dark:text-yellow-200 hover:bg-yellow-100 dark:hover:bg-yellow-800/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-yellow-50 focus:ring-yellow-600"
									>
										Review Expiring Contracts →
									</a>
								</div>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Key Risk Metrics -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
		<!-- Total Entities -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-blue-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Entities</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalEntities}</p>
						<div class="flex items-center text-sm">
							<span class="text-blue-600 font-medium">{data.metrics.activeEntities} active</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/third-party/entities`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View all entities →
					</a>
				</div>
			</div>
		</div>

		<!-- Risk Distribution -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">High Risk Entities</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.criticalRiskEntities + data.metrics.highRiskEntities}</p>
						<div class="flex items-center text-sm">
							<span class="text-red-600 font-medium">{data.metrics.overallRiskLevel}% of total</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/third-party/entities?risk_level=critical,high`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						Review high risk →
					</a>
				</div>
			</div>
		</div>

		<!-- Compliance Rate -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Compliance Rate</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.complianceRate}%</p>
						<div class="flex items-center text-sm">
							<span class={`font-medium ${data.metrics.complianceRate >= 90 ? 'text-green-600' : data.metrics.complianceRate >= 75 ? 'text-yellow-600' : 'text-red-600'}`}>
								{data.metrics.complianceRate >= 90 ? 'Excellent' : data.metrics.complianceRate >= 75 ? 'Good' : 'Needs Attention'}
							</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/analytics/third-party`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View compliance →
					</a>
				</div>
			</div>
		</div>

		<!-- Contract Health -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-yellow-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Contract Health</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.contractHealth}%</p>
						<div class="flex items-center text-sm">
							<span class="text-yellow-600 font-medium">{data.metrics.expiringContracts} expiring soon</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/third-party/contracts`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						Manage contracts →
					</a>
				</div>
			</div>
		</div>
	</div>

	<!-- Entity Type Distribution -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Entity Distribution by Type</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
				<div class="text-center">
					<div class="text-2xl font-bold text-blue-600">{data.metrics.vendors}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Vendors</div>
					<div class="mt-1 text-xs text-blue-600">Core suppliers</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-green-600">{data.metrics.contractors}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Contractors</div>
					<div class="mt-1 text-xs text-green-600">Service providers</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-purple-600">{data.metrics.partners}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Partners</div>
					<div class="mt-1 text-xs text-purple-600">Strategic alliances</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-orange-600">{data.metrics.suppliers}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Suppliers</div>
					<div class="mt-1 text-xs text-orange-600">Material providers</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Quick Actions -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Risk Management Actions</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<a
					href={`${base}/third-party/entities/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Onboard New Entity</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Add vendor, contractor, or partner</p>
					</div>
				</a>

				<a
					href={`${base}/third-party/assessments/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Conduct Risk Assessment</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Evaluate third party risk profile</p>
					</div>
				</a>

				<a
					href={`${base}/third-party/contracts`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Manage Contracts</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Track contract lifecycle and renewals</p>
					</div>
				</a>

				<a
					href={`${base}/analytics/third-party`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Risk Analytics</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Third party risk dashboards and reports</p>
					</div>
				</a>
			</div>
		</div>
	</div>

	<!-- Recent Activity -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
		<!-- Recent Entities -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent Third Party Entities</h3>
			</div>
			<div class="p-6">
				{#if data.metrics.recentEntities.length > 0}
					<div class="space-y-4">
						{#each data.metrics.recentEntities as entity}
							<div class="flex items-center justify-between">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class={`h-8 w-8 rounded-full flex items-center justify-center ${
											entity.entity_type === 'vendor' ? 'bg-blue-500' :
											entity.entity_type === 'contractor' ? 'bg-green-500' :
											entity.entity_type === 'partner' ? 'bg-purple-500' :
											'bg-orange-500'
										}`}>
											<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{entity.entity_name}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400 capitalize">
											{entity.entity_type}
										</p>
									</div>
								</div>
								<div class="flex flex-col items-end">
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mb-1 ${
										entity.risk_level === 'critical' ? 'bg-red-100 text-red-800' :
										entity.risk_level === 'high' ? 'bg-orange-100 text-orange-800' :
										entity.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
										'bg-green-100 text-green-800'
									}`}>
										{entity.risk_level} risk
									</span>
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
										entity.compliance_status === 'compliant' ? 'bg-green-100 text-green-800' :
										entity.compliance_status === 'non_compliant' ? 'bg-red-100 text-red-800' :
										'bg-yellow-100 text-yellow-800'
									}`}>
										{entity.compliance_status}
									</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No third party entities onboarded yet.</p>
				{/if}
			</div>
		</div>

		<!-- Risk and Compliance Alerts -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Risk & Compliance Alerts</h3>
			</div>
			<div class="p-6">
				<div class="space-y-4">
					{#if data.metrics.criticalRiskEntitiesList.length > 0}
						{#each data.metrics.criticalRiskEntitiesList as entity}
							<div class="border border-red-200 dark:border-red-700 rounded-lg p-4 bg-red-50 dark:bg-red-900/20">
								<div class="flex items-center justify-between">
									<div class="flex items-center">
										<div class="flex-shrink-0">
											<div class="h-8 w-8 rounded-full bg-red-500 flex items-center justify-center">
												<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
												</svg>
											</div>
										</div>
										<div class="ml-3">
											<p class="text-sm font-medium text-red-900 dark:text-red-200 truncate">
												{entity.entity_name}
											</p>
											<p class="text-sm text-red-700 dark:text-red-300">
												Critical risk level requires immediate attention
											</p>
										</div>
									</div>
									<div class="flex flex-col items-end">
										<a
											href={`${base}/third-party/entities/${entity.id}`}
											class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 dark:bg-red-800 dark:text-red-200 dark:hover:bg-red-700"
										>
											Review
										</a>
									</div>
								</div>
							</div>
						{/each}
					{/if}

					{#if data.metrics.expiringContractsList.length > 0}
						{#each data.metrics.expiringContractsList as entity}
							<div class="border border-yellow-200 dark:border-yellow-700 rounded-lg p-4 bg-yellow-50 dark:bg-yellow-900/20">
								<div class="flex items-center justify-between">
									<div class="flex items-center">
										<div class="flex-shrink-0">
											<div class="h-8 w-8 rounded-full bg-yellow-500 flex items-center justify-center">
												<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
												</svg>
											</div>
										</div>
										<div class="ml-3">
											<p class="text-sm font-medium text-yellow-900 dark:text-yellow-200 truncate">
												{entity.entity_name}
											</p>
											<p class="text-sm text-yellow-700 dark:text-yellow-300">
												Contract expires soon - renewal required
											</p>
										</div>
									</div>
									<div class="flex flex-col items-end">
										<a
											href={`${base}/third-party/entities/${entity.id}/contracts`}
											class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-yellow-700 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 dark:bg-yellow-800 dark:text-yellow-200 dark:hover:bg-yellow-700"
										>
											Renew
										</a>
									</div>
								</div>
							</div>
						{/each}
					{/if}

					{#if data.metrics.criticalRiskEntitiesList.length === 0 && data.metrics.expiringContractsList.length === 0}
						<div class="text-center py-6">
							<svg class="mx-auto h-12 w-12 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
							<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">All Clear</h3>
							<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">No critical risks or expiring contracts.</p>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
