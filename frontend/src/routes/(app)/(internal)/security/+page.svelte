<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: breadcrumbs = [
		{ label: 'Security Operations Dashboard', href: `${base}/security` }
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
			Security Operations Center
		</h1>
		<p class="mt-2 text-lg text-gray-600 dark:text-gray-400">
			Real-time incident response and security monitoring dashboard
		</p>
	</div>

	<!-- Critical Alerts Banner -->
	{#if data.metrics.criticalIncidents > 0}
		<div class="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 p-4 mb-6">
			<div class="flex">
				<div class="flex-shrink-0">
					<svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
					</svg>
				</div>
				<div class="ml-3">
					<h3 class="text-sm font-medium text-red-800 dark:text-red-200">
						Critical Security Incidents Active
					</h3>
					<div class="mt-2 text-sm text-red-700 dark:text-red-300">
						<p>{data.metrics.criticalIncidents} critical incidents require immediate attention.</p>
					</div>
					<div class="mt-4">
						<div class="-mx-2 -my-1.5 flex">
							<a
								href={`${base}/security/incidents?severity=critical&status=active`}
								class="bg-red-50 dark:bg-red-900/20 px-2 py-1.5 rounded-md text-sm font-medium text-red-800 dark:text-red-200 hover:bg-red-100 dark:hover:bg-red-800/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
							>
								View Critical Incidents →
							</a>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Key Security Metrics -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
		<!-- Total Incidents -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Incidents</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.totalIncidents}</p>
						<div class="flex items-center text-sm">
							<span class="text-red-600 font-medium">{data.metrics.activeIncidents} active</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/security/incidents`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View all incidents →
					</a>
				</div>
			</div>
		</div>

		<!-- Critical Incidents -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-red-600 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Critical Incidents</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.criticalIncidents}</p>
						<div class="flex items-center text-sm">
							<span class="text-red-600 font-medium">Immediate response required</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/security/incidents?severity=critical`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View critical incidents →
					</a>
				</div>
			</div>
		</div>

		<!-- SLA Compliance -->
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
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">SLA Compliance</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.slaComplianceRate}%</p>
						<div class="flex items-center text-sm">
							<span class={`font-medium ${data.metrics.slaComplianceRate >= 95 ? 'text-green-600' : data.metrics.slaComplianceRate >= 80 ? 'text-yellow-600' : 'text-red-600'}`}>
								{data.metrics.slaComplianceRate >= 95 ? 'Excellent' : data.metrics.slaComplianceRate >= 80 ? 'Good' : 'Needs Improvement'}
							</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/analytics/security`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View SLA analytics →
					</a>
				</div>
			</div>
		</div>

		<!-- Resolution Rate -->
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-6">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<div class="h-8 w-8 rounded-lg bg-blue-500 flex items-center justify-center">
							<svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<p class="text-sm font-medium text-gray-500 dark:text-gray-400">Resolution Rate</p>
						<p class="text-2xl font-semibold text-gray-900 dark:text-white">{data.metrics.resolutionRate}%</p>
						<div class="flex items-center text-sm">
							<span class="text-blue-600 font-medium">{data.metrics.resolvedIncidents} resolved</span>
						</div>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 dark:bg-gray-700 px-6 py-3">
				<div class="text-sm">
					<a href={`${base}/analytics/security`} class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
						View resolution metrics →
					</a>
				</div>
			</div>
		</div>
	</div>

	<!-- Incident Severity Distribution -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Incident Severity Distribution</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
				<div class="text-center">
					<div class="text-2xl font-bold text-red-600">{data.metrics.criticalIncidents}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Critical</div>
					<div class="mt-1 text-xs text-red-600">Immediate Response</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-orange-600">{data.metrics.highSeverityIncidents}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">High</div>
					<div class="mt-1 text-xs text-orange-600">24h Response</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-yellow-600">{data.metrics.mediumSeverityIncidents}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Medium</div>
					<div class="mt-1 text-xs text-yellow-600">72h Response</div>
				</div>
				<div class="text-center">
					<div class="text-2xl font-bold text-blue-600">{data.metrics.lowSeverityIncidents}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">Low</div>
					<div class="mt-1 text-xs text-blue-600">Standard Response</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Quick Actions -->
	<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-medium text-gray-900 dark:text-white">Incident Response Actions</h3>
		</div>
		<div class="p-6">
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<a
					href={`${base}/security/incidents/new`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Report New Incident</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Log security incident for response</p>
					</div>
				</a>

				<a
					href={`${base}/security/incidents?status=active`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Active Incidents</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Monitor ongoing incident response</p>
					</div>
				</a>

				<a
					href={`${base}/analytics/security`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Security Analytics</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">View threat intelligence and trends</p>
					</div>
				</a>

				<a
					href={`${base}/security/playbooks`}
					class="flex items-center p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm font-medium text-gray-900 dark:text-white">Response Playbooks</p>
						<p class="text-sm text-gray-500 dark:text-gray-400">Access incident response procedures</p>
					</div>
				</a>
			</div>
		</div>
	</div>

	<!-- Recent Activity -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
		<!-- Recent Incidents -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Recent Security Incidents</h3>
			</div>
			<div class="p-6">
				{#if data.metrics.recentIncidents.length > 0}
					<div class="space-y-4">
						{#each data.metrics.recentIncidents as incident}
							<div class="flex items-center justify-between">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class={`h-8 w-8 rounded-full flex items-center justify-center ${
											incident.severity === 'critical' ? 'bg-red-500' :
											incident.severity === 'high' ? 'bg-orange-500' :
											incident.severity === 'medium' ? 'bg-yellow-500' :
											'bg-blue-500'
										}`}>
											<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{incident.incident_title}
										</p>
										<p class="text-sm text-gray-500 dark:text-gray-400">
											{incident.incident_type} • {new Date(incident.detected_at).toLocaleDateString()}
										</p>
									</div>
								</div>
								<div class="flex flex-col items-end">
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mb-1 ${
										incident.severity === 'critical' ? 'bg-red-100 text-red-800' :
										incident.severity === 'high' ? 'bg-orange-100 text-orange-800' :
										incident.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
										'bg-blue-100 text-blue-800'
									}`}>
										{incident.severity}
									</span>
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
										incident.status === 'resolved' ? 'bg-green-100 text-green-800' :
										incident.status === 'active' ? 'bg-red-100 text-red-800' :
										incident.status === 'investigating' ? 'bg-yellow-100 text-yellow-800' :
										'bg-gray-100 text-gray-800'
									}`}>
										{incident.status}
									</span>
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-gray-500 dark:text-gray-400">No security incidents recorded yet.</p>
				{/if}
			</div>
		</div>

		<!-- Critical Incidents Alert -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white">Critical Incidents Requiring Attention</h3>
			</div>
			<div class="p-6">
				{#if data.metrics.criticalIncidentsList.length > 0}
					<div class="space-y-4">
						{#each data.metrics.criticalIncidentsList as incident}
							<div class="border border-red-200 dark:border-red-700 rounded-lg p-4 bg-red-50 dark:bg-red-900/20">
								<div class="flex items-center justify-between">
									<div class="flex items-center">
										<div class="flex-shrink-0">
											<div class="h-8 w-8 rounded-full bg-red-500 flex items-center justify-center">
												<svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
												</svg>
											</div>
										</div>
										<div class="ml-3">
											<p class="text-sm font-medium text-red-900 dark:text-red-200 truncate">
												{incident.incident_title}
											</p>
											<p class="text-sm text-red-700 dark:text-red-300">
												{incident.incident_type} • Detected {new Date(incident.detected_at).toLocaleDateString()}
											</p>
											<p class="text-xs text-red-600 dark:text-red-400 mt-1">
												Response Time: {
													(() => {
														const now = new Date();
														const detected = new Date(incident.detected_at);
														const diffHours = Math.floor((now - detected) / (1000 * 60 * 60));
														return `${diffHours}h ${Math.floor(((now - detected) % (1000 * 60 * 60)) / (1000 * 60))}m`;
													})()
												}
											</p>
										</div>
									</div>
									<div class="flex flex-col items-end">
										<a
											href={`${base}/security/incidents/${incident.id}`}
											class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 dark:bg-red-800 dark:text-red-200 dark:hover:bg-red-700"
										>
											Respond Now
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
						<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">All Clear</h3>
						<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">No critical incidents currently active.</p>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
