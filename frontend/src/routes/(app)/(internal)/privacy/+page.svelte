<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: breadcrumbs = [
		{ label: 'Privacy Program Dashboard', href: `${base}/privacy` }
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
			Privacy Program Dashboard
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Comprehensive overview of your privacy compliance and data protection program
		</p>
	</div>

	<!-- Key Metrics Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
		<!-- Data Assets -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Data Assets</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalDataAssets}</p>
						<div class="flex items-center text-sm">
							<span class="text-green-600 font-medium">{data.metrics.compliancePercentage}% compliant</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/privacy/data-assets`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View all assets →
					</a>
				</div>
			</div>
		</div>

		<!-- Consent Records -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Consent Records</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalConsents}</p>
						<div class="flex items-center text-sm">
							<span class="text-green-600 font-medium">{data.metrics.consentRetentionRate}% active</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/privacy/consent-records`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						Manage consents →
					</a>
				</div>
			</div>
		</div>

		<!-- Data Subject Rights -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-purple-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Rights Requests</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalRightsRequests}</p>
						<div class="flex items-center text-sm">
							<span class="text-green-600 font-medium">{data.metrics.rightsFulfillmentRate}% fulfilled</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/privacy/data-subject-rights`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View requests →
					</a>
				</div>
			</div>
		</div>

		<!-- Compliance Status -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-yellow-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Compliance Health</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.compliancePercentage}%</p>
						<div class="flex items-center text-sm">
							<span class={`font-medium ${data.metrics.compliancePercentage >= 80 ? 'text-green-600' : data.metrics.compliancePercentage >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
								{data.metrics.compliancePercentage >= 80 ? 'Healthy' : data.metrics.compliancePercentage >= 60 ? 'Needs Attention' : 'Critical'}
							</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/analytics/privacy`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View analytics →
					</a>
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
					href={`${base}/privacy/data-assets/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Register Data Asset</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Add new data asset for compliance tracking</p>
					</div>
				</a>

				<a
					href={`${base}/privacy/consent-records/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Record Consent</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Document new data subject consent</p>
					</div>
				</a>

				<a
					href={`${base}/privacy/data-subject-rights/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Handle Rights Request</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Process GDPR data subject rights</p>
					</div>
				</a>

				<a
					href={`${base}/analytics/privacy`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">View Analytics</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Privacy compliance analytics and reports</p>
					</div>
				</a>
			</div>
		</div>
	</div>

	<!-- Recent Activity -->
	<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
		<!-- Recent Data Assets -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent Data Assets</h3>
			</div>
			<div class="p-6">
				{#if data.recentAssets.length > 0}
					<div class="space-y-4">
						{#each data.recentAssets as asset}
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
											{asset.asset_name}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											{asset.asset_id}
										</p>
									</div>
								</div>
								<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
									asset.compliance_status === 'compliant' ? 'bg-green-100 text-green-800' :
									asset.compliance_status === 'non_compliant' ? 'bg-red-100 text-red-800' :
									'bg-gray-100 text-gray-800'
								}`}>
									{asset.compliance_status}
								</span>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No data assets registered yet.</p>
				{/if}
			</div>
		</div>

		<!-- Recent Consent Records -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent Consents</h3>
			</div>
			<div class="p-6">
				{#if data.recentConsents.length > 0}
					<div class="space-y-4">
						{#each data.recentConsents as consent}
							<div class="flex items-center justify-between">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="h-8 w-8 rounded-full bg-green-500 flex items-center justify-center">
											<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{consent.consent_id}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											{consent.data_subject_id}
										</p>
									</div>
								</div>
								<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
									consent.status === 'active' ? 'bg-green-100 text-green-800' :
									consent.status === 'withdrawn' ? 'bg-red-100 text-red-800' :
									'bg-gray-100 text-gray-800'
								}`}>
									{consent.status}
								</span>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No consent records yet.</p>
				{/if}
			</div>
		</div>

		<!-- Recent Rights Requests -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Rights Requests</h3>
			</div>
			<div class="p-6">
				{#if data.recentRights.length > 0}
					<div class="space-y-4">
						{#each data.recentRights as right}
							<div class="flex items-center justify-between">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="h-8 w-8 rounded-full bg-purple-500 flex items-center justify-center">
											<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{right.request_id}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											{right.primary_right}
										</p>
									</div>
								</div>
								<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
									right.status === 'completed' ? 'bg-green-100 text-green-800' :
									right.status === 'rejected' ? 'bg-red-100 text-red-800' :
									right.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
									'bg-gray-100 text-gray-800'
								}`}>
									{right.status}
								</span>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No rights requests yet.</p>
				{/if}
			</div>
		</div>
	</div>
</div>
