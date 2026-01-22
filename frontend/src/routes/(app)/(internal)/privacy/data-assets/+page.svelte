<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { safeTranslate } from '$lib/utils/i18n';
	import { urlModel } from '$lib/stores';
	import type { PageData } from './$types';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import { onMount } from 'svelte';

	export let data: PageData;

	let model: any = null;
	let tableConfig: any = null;

	onMount(() => {
		model = data.model;
		tableConfig = {
			model: model,
			data: data.dataAssets,
			count: data.count,
			next: data.next,
			previous: data.previous,
			queryParams: data.queryParams,
			columns: [
				{
					field: 'asset_id',
					header: 'Asset ID',
					sortable: true,
					width: '150px'
				},
				{
					field: 'asset_name',
					header: 'Asset Name',
					sortable: true,
					width: '200px'
				},
				{
					field: 'primary_data_category',
					header: 'Data Category',
					sortable: true,
					width: '150px',
					format: (value: string) => {
						const categories = {
							'personal_data': 'Personal Data',
							'sensitive_personal_data': 'Sensitive Personal',
							'special_category_data': 'Special Category',
							'genetic_data': 'Genetic Data',
							'biometric_data': 'Biometric Data',
							'health_data': 'Health Data'
						};
						return categories[value] || value;
					}
				},
				{
					field: 'sensitivity_level',
					header: 'Sensitivity',
					sortable: true,
					width: '120px',
					format: (value: string) => {
						const levels = {
							'public': 'Public',
							'internal': 'Internal',
							'confidential': 'Confidential',
							'restricted': 'Restricted',
							'highly_restricted': 'Highly Restricted'
						};
						return levels[value] || value;
					}
				},
				{
					field: 'compliance_status',
					header: 'Compliance Status',
					sortable: true,
					width: '140px',
					format: (value: string) => {
						const statuses = {
							'compliant': 'Compliant',
							'non_compliant': 'Non-Compliant',
							'under_review': 'Under Review',
							'not_assessed': 'Not Assessed'
						};
						return statuses[value] || value;
					},
					cellClass: (value: string) => {
						const classes = {
							'compliant': 'text-green-600',
							'non_compliant': 'text-red-600',
							'under_review': 'text-yellow-600',
							'not_assessed': 'text-gray-600'
						};
						return classes[value] || '';
					}
				},
				{
					field: 'pia_required',
					header: 'PIA Required',
					sortable: true,
					width: '120px',
					format: (value: boolean) => value ? 'Yes' : 'No'
				},
				{
					field: 'estimated_data_subjects',
					header: 'Data Subjects',
					sortable: true,
					width: '120px',
					format: (value: number) => value ? value.toLocaleString() : 'N/A'
				}
			],
			actions: [
				{
					label: 'View Details',
					icon: 'eye',
					action: 'view',
					condition: () => true
				},
				{
					label: 'Edit',
					icon: 'edit',
					action: 'edit',
					condition: () => true
				},
				{
					label: 'Conduct PIA',
					icon: 'clipboard-check',
					action: 'pia',
					condition: (item: any) => item.pia_required && !item.pia_completed
				}
			]
		};
	});

	$: breadcrumbs = [
		{ label: 'Privacy', href: `${base}/privacy` },
		{ label: 'Data Assets', href: `${base}/privacy/data-assets` }
	];
</script>

<svelte:head>
	<title>{data.title}</title>
</svelte:head>

<Breadcrumbs items={breadcrumbs} />

<div class="flex flex-col gap-4">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
				{safeTranslate('Privacy Data Assets')}
			</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">
				Manage privacy data assets and compliance requirements
			</p>
		</div>
		<div class="flex gap-2">
			<a
				href={`${base}/privacy/data-assets/new`}
				class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
			>
				<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
				</svg>
				New Data Asset
			</a>
		</div>
	</div>

	<!-- Compliance Overview Cards -->
	<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-5">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-5 w-0 flex-1">
						<dl>
							<dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
								Compliant Assets
							</dt>
							<dd class="text-lg font-medium text-gray-900 dark:text-white">
								{data.dataAssets.filter((asset: any) => asset.compliance_status === 'compliant').length}
							</dd>
						</dl>
					</div>
				</div>
			</div>
		</div>

		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-5">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
						</svg>
					</div>
					<div class="ml-5 w-0 flex-1">
						<dl>
							<dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
								Non-Compliant
							</dt>
							<dd class="text-lg font-medium text-gray-900 dark:text-white">
								{data.dataAssets.filter((asset: any) => asset.compliance_status === 'non_compliant').length}
							</dd>
						</dl>
					</div>
				</div>
			</div>
		</div>

		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-5">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-5 w-0 flex-1">
						<dl>
							<dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
								PIA Required
							</dt>
							<dd class="text-lg font-medium text-gray-900 dark:text-white">
								{data.dataAssets.filter((asset: any) => asset.pia_required && !asset.pia_completed).length}
							</dd>
						</dl>
					</div>
				</div>
			</div>
		</div>

		<div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
			<div class="p-5">
				<div class="flex items-center">
					<div class="flex-shrink-0">
						<svg class="h-6 w-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
						</svg>
					</div>
					<div class="ml-5 w-0 flex-1">
						<dl>
							<dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
								Total Assets
							</dt>
							<dd class="text-lg font-medium text-gray-900 dark:text-white">
								{data.count}
							</dd>
						</dl>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Data Assets Table -->
	<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
		{#if tableConfig}
			<ModelTable {tableConfig} />
		{:else}
			<div class="p-6 text-center">
				<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
				</svg>
				<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">Loading data assets...</h3>
			</div>
		{/if}
	</div>
</div>
