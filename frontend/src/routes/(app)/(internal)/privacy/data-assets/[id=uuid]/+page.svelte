<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { safeTranslate } from '$lib/utils/i18n';
	import { superForm } from 'sveltekit-superforms/client';
	import { zod } from 'sveltekit-superforms/adapters';
	import { dataAssetSchema } from '$lib/utils/schemas';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import type { PageData, ActionData } from './$types';

	export let data: PageData;
	export let form: ActionData;

	let activeTab = 'overview';
	let editing = false;

	const formStore = superForm(data.form, {
		validators: zod(dataAssetSchema),
		onUpdated: ({ form }) => {
			if (form.valid && $page.form?.success) {
				editing = false;
				invalidateAll();
			}
		}
	});

	const tabs = [
		{ id: 'overview', label: 'Overview', icon: 'eye' },
		{ id: 'compliance', label: 'Compliance', icon: 'shield-check' },
		{ id: 'processing', label: 'Processing', icon: 'cog' },
		{ id: 'consent', label: 'Consent', icon: 'check-circle' },
		{ id: 'rights', label: 'Subject Rights', icon: 'user-check' },
		{ id: 'security', label: 'Security', icon: 'lock' }
	];

	const dataCategories = {
		'personal_data': 'Personal Data',
		'sensitive_personal_data': 'Sensitive Personal Data',
		'special_category_data': 'Special Category Data',
		'criminal_conviction_data': 'Criminal Conviction Data',
		'genetic_data': 'Genetic Data',
		'biometric_data': 'Biometric Data',
		'health_data': 'Health Data',
		'financial_data': 'Financial Data',
		'communication_data': 'Communication Data',
		'location_data': 'Location Data',
		'online_identifier_data': 'Online Identifier Data',
		'racial_ethnic_data': 'Racial/Ethnic Origin Data',
		'political_opinion_data': 'Political Opinion Data',
		'religious_belief_data': 'Religious Belief Data',
		'trade_union_data': 'Trade Union Membership Data',
		'sexual_orientation_data': 'Sexual Orientation Data'
	};

	const sensitivityLevels = {
		'public': { label: 'Public', color: 'bg-green-100 text-green-800' },
		'internal': { label: 'Internal', color: 'bg-blue-100 text-blue-800' },
		'confidential': { label: 'Confidential', color: 'bg-yellow-100 text-yellow-800' },
		'restricted': { label: 'Restricted', color: 'bg-orange-100 text-orange-800' },
		'highly_restricted': { label: 'Highly Restricted', color: 'bg-red-100 text-red-800' }
	};

	const complianceStatuses = {
		'compliant': { label: 'Compliant', color: 'bg-green-100 text-green-800' },
		'non_compliant': { label: 'Non-Compliant', color: 'bg-red-100 text-red-800' },
		'under_review': { label: 'Under Review', color: 'bg-yellow-100 text-yellow-800' },
		'not_assessed': { label: 'Not Assessed', color: 'bg-gray-100 text-gray-800' }
	};

	$: breadcrumbs = [
		{ label: 'Privacy', href: `${base}/privacy` },
		{ label: 'Data Assets', href: `${base}/privacy/data-assets` },
		{ label: data.dataAsset.asset_name, href: `${base}/privacy/data-assets/${data.dataAsset.id}` }
	];
</script>

<svelte:head>
	<title>{data.title}</title>
</svelte:head>

<Breadcrumbs items={breadcrumbs} />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
	<!-- Header -->
	<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg mb-6">
		<div class="px-4 py-5 sm:p-6">
			<div class="flex items-center justify-between">
				<div class="flex items-center">
					<div class="flex-shrink-0 h-12 w-12">
						<div class="h-12 w-12 rounded-lg bg-blue-500 flex items-center justify-center">
							<svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
							</svg>
						</div>
					</div>
					<div class="ml-4">
						<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
							{data.dataAsset.asset_name}
						</h1>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							Asset ID: {data.dataAsset.asset_id}
						</p>
					</div>
				</div>
				<div class="flex items-center space-x-3">
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${sensitivityLevels[data.dataAsset.sensitivity_level]?.color || 'bg-gray-100 text-gray-800'}`}>
						{sensitivityLevels[data.dataAsset.sensitivity_level]?.label || data.dataAsset.sensitivity_level}
					</span>
					<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${complianceStatuses[data.dataAsset.compliance_status]?.color || 'bg-gray-100 text-gray-800'}`}>
						{complianceStatuses[data.dataAsset.compliance_status]?.label || data.dataAsset.compliance_status}
					</span>
					<div class="flex space-x-2">
						{#if data.dataAsset.pia_required && !data.dataAsset.pia_completed}
							<form method="POST" action="?/conduct_pia" use:enhance>
								<button
									type="submit"
									class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
								>
									Conduct PIA
								</button>
							</form>
						{/if}
						<button
							on:click={() => editing = !editing}
							class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 text-sm leading-4 font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
						>
							<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
							</svg>
							Edit
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Tabs -->
	<div class="border-b border-gray-200 dark:border-gray-700 mb-6">
		<nav class="-mb-px flex space-x-8">
			{#each tabs as tab}
				<button
					on:click={() => activeTab = tab.id}
					class={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
						activeTab === tab.id
							? 'border-blue-500 text-blue-600 dark:text-blue-400'
							: 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
					}`}
				>
					<svg class="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						{#if tab.icon === 'eye'}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
						{:else if tab.icon === 'shield-check'}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
						{:else if tab.icon === 'cog'}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
						{:else if tab.icon === 'check-circle'}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
						{:else if tab.icon === 'user-check'}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
						{:else if tab.icon === 'lock'}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
						{/if}
					</svg>
					{tab.label}
				</button>
			{/each}
		</nav>
	</div>

	<!-- Tab Content -->
	<div class="space-y-6">
		{#if activeTab === 'overview'}
			<!-- Overview Tab -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Basic Information -->
				<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
					<div class="px-4 py-5 sm:p-6">
						<h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
							Basic Information
						</h3>
						<dl class="space-y-3">
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Asset Name</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">{data.dataAsset.asset_name}</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Asset ID</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">{data.dataAsset.asset_id}</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Primary Data Category</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{dataCategories[data.dataAsset.primary_data_category] || data.dataAsset.primary_data_category}
								</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Sensitivity Level</dt>
								<dd class="mt-1">
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${sensitivityLevels[data.dataAsset.sensitivity_level]?.color || 'bg-gray-100 text-gray-800'}`}>
										{sensitivityLevels[data.dataAsset.sensitivity_level]?.label || data.dataAsset.sensitivity_level}
									</span>
								</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Estimated Data Subjects</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{data.dataAsset.estimated_data_subjects ? data.dataAsset.estimated_data_subjects.toLocaleString() : 'Not specified'}
								</dd>
							</div>
						</dl>
					</div>
				</div>

				<!-- Compliance Status -->
				<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
					<div class="px-4 py-5 sm:p-6">
						<h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
							Compliance Status
						</h3>
						<dl class="space-y-3">
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Compliance Status</dt>
								<dd class="mt-1">
									<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${complianceStatuses[data.dataAsset.compliance_status]?.color || 'bg-gray-100 text-gray-800'}`}>
										{complianceStatuses[data.dataAsset.compliance_status]?.label || data.dataAsset.compliance_status}
									</span>
								</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">PIA Required</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{data.dataAsset.pia_required ? 'Yes' : 'No'}
									{#if data.dataAsset.pia_completed}
										<span class="ml-2 text-green-600">(Completed)</span>
									{/if}
								</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">DPO Review Required</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{data.dataAsset.dpo_review_required ? 'Yes' : 'No'}
									{#if data.dataAsset.dpo_reviewed}
										<span class="ml-2 text-green-600">(Completed)</span>
									{/if}
								</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Last Assessment</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{data.dataAsset.last_assessment_date ? new Date(data.dataAsset.last_assessment_date).toLocaleDateString() : 'Not assessed'}
								</dd>
							</div>
						</dl>
					</div>
				</div>
			</div>

			<!-- Description -->
			{#if data.dataAsset.asset_description}
				<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
					<div class="px-4 py-5 sm:p-6">
						<h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
							Description
						</h3>
						<p class="text-sm text-gray-700 dark:text-gray-300">
							{data.dataAsset.asset_description}
						</p>
					</div>
				</div>
			{/if}
		{:else if activeTab === 'compliance'}
			<!-- Compliance Tab -->
			<div class="space-y-6">
				<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
					<div class="px-4 py-5 sm:p-6">
						<h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
							Compliance Details
						</h3>
						<dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Legal Bases</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{#if data.dataAsset.legal_bases && data.dataAsset.legal_bases.length > 0}
										<ul class="list-disc list-inside">
											{#each data.dataAsset.legal_bases as basis}
												<li>{basis}</li>
											{/each}
										</ul>
									{:else}
										<span class="text-gray-500">Not specified</span>
									{/if}
								</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Processing Purposes</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{#if data.dataAsset.processing_purposes && data.dataAsset.processing_purposes.length > 0}
										<ul class="list-disc list-inside">
											{#each data.dataAsset.processing_purposes as purpose}
												<li>{purpose}</li>
											{/each}
										</ul>
									{:else}
										<span class="text-gray-500">Not specified</span>
									{/if}
								</dd>
							</div>
						</dl>
					</div>
				</div>
			</div>
		{:else if activeTab === 'consent'}
			<!-- Consent Tab -->
			<div class="space-y-6">
				<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
					<div class="px-4 py-5 sm:p-6">
						<h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
							Consent Records ({data.consentRecords.length})
						</h3>
						{#if data.consentRecords.length > 0}
							<div class="space-y-4">
								{#each data.consentRecords as record}
									<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
										<div class="flex items-center justify-between">
											<div>
												<h4 class="text-sm font-medium text-gray-900 dark:text-white">
													Consent {record.consent_id}
												</h4>
												<p class="text-sm text-gray-500 dark:text-gray-400">
													Given: {new Date(record.consent_date).toLocaleDateString()}
												</p>
											</div>
											<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
												record.status === 'active' ? 'bg-green-100 text-green-800' :
												record.status === 'withdrawn' ? 'bg-red-100 text-red-800' :
												'bg-gray-100 text-gray-800'
											}`}>
												{record.status}
											</span>
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<p class="text-sm text-gray-500 dark:text-gray-400">No consent records found for this data asset.</p>
						{/if}
					</div>
				</div>
			</div>
		{:else if activeTab === 'rights'}
			<!-- Subject Rights Tab -->
			<div class="space-y-6">
				<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
					<div class="px-4 py-5 sm:p-6">
						<h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
							Data Subject Rights Requests ({data.dataSubjectRights.length})
						</h3>
						{#if data.dataSubjectRights.length > 0}
							<div class="space-y-4">
								{#each data.dataSubjectRights as right}
									<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
										<div class="flex items-center justify-between">
											<div>
												<h4 class="text-sm font-medium text-gray-900 dark:text-white">
													Request {right.request_id}
												</h4>
												<p class="text-sm text-gray-500 dark:text-gray-400">
													{right.primary_right} - {new Date(right.received_date).toLocaleDateString()}
												</p>
											</div>
											<span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
												right.status === 'completed' ? 'bg-green-100 text-green-800' :
												right.status === 'rejected' ? 'bg-red-100 text-red-800' :
												right.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
												'bg-gray-100 text-gray-800'
											}`}>
												{right.status}
											</span>
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<p class="text-sm text-gray-500 dark:text-gray-400">No data subject rights requests found for this data asset.</p>
						{/if}
					</div>
				</div>
			</div>
		{:else if activeTab === 'security'}
			<!-- Security Tab -->
			<div class="space-y-6">
				<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
					<div class="px-4 py-5 sm:p-6">
						<h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
							Security Measures
						</h3>
						<dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Security Measures</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{#if data.dataAsset.security_measures && data.dataAsset.security_measures.length > 0}
										<ul class="list-disc list-inside">
											{#each data.dataAsset.security_measures as measure}
												<li>{measure}</li>
											{/each}
										</ul>
									{:else}
										<span class="text-gray-500">Not specified</span>
									{/if}
								</dd>
							</div>
							<div>
								<dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Encryption Methods</dt>
								<dd class="mt-1 text-sm text-gray-900 dark:text-white">
									{#if data.dataAsset.encryption_methods && data.dataAsset.encryption_methods.length > 0}
										<ul class="list-disc list-inside">
											{#each data.dataAsset.encryption_methods as method}
												<li>{method}</li>
											{/each}
										</ul>
									{:else}
										<span class="text-gray-500">Not specified</span>
									{/if}
								</dd>
							</div>
						</dl>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>
