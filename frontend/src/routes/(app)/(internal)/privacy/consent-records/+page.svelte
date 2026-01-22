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
			data: data.consentRecords,
			count: data.count,
			next: data.next,
			previous: data.previous,
			queryParams: data.queryParams,
			columns: [
				{
					field: 'consent_id',
					header: 'Consent ID',
					sortable: true,
					width: '150px'
				},
				{
					field: 'data_subject_id',
					header: 'Data Subject',
					sortable: true,
					width: '180px'
				},
				{
					field: 'data_subject_type',
					header: 'Subject Type',
					sortable: true,
					width: '120px',
					format: (value: string) => {
						const types = {
							'customer': 'Customer',
							'employee': 'Employee',
							'website_user': 'Website User',
							'prospect': 'Prospect',
							'supplier': 'Supplier',
							'other': 'Other'
						};
						return types[value] || value;
					}
				},
				{
					field: 'consent_method',
					header: 'Method',
					sortable: true,
					width: '130px',
					format: (value: string) => {
						const methods = {
							'digital_signature': 'Digital Signature',
							'checkbox': 'Checkbox',
							'written': 'Written',
							'verbal': 'Verbal',
							'implied': 'Implied',
							'opt_in_email': 'Opt-in Email',
							'opt_in_form': 'Opt-in Form'
						};
						return methods[value] || value;
					}
				},
				{
					field: 'consent_date',
					header: 'Consent Date',
					sortable: true,
					width: '140px',
					format: (value: string) => value ? new Date(value).toLocaleDateString() : 'N/A'
				},
				{
					field: 'valid_until',
					header: 'Valid Until',
					sortable: true,
					width: '140px',
					format: (value: string) => value ? new Date(value).toLocaleDateString() : 'No expiry'
				},
				{
					field: 'status',
					header: 'Status',
					sortable: true,
					width: '120px',
					format: (value: string) => {
						const statuses = {
							'active': 'Active',
							'expired': 'Expired',
							'withdrawn': 'Withdrawn',
							'revoked': 'Revoked',
							'pending_verification': 'Pending',
							'invalid': 'Invalid'
						};
						return statuses[value] || value;
					},
					cellClass: (value: string) => {
						const classes = {
							'active': 'text-green-600',
							'expired': 'text-orange-600',
							'withdrawn': 'text-red-600',
							'revoked': 'text-red-600',
							'pending_verification': 'text-yellow-600',
							'invalid': 'text-gray-600'
						};
						return classes[value] || '';
					}
				},
				{
					field: 'processing_purposes_count',
					header: 'Purposes',
					sortable: true,
					width: '100px',
					format: (value: number) => value || 0
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
					label: 'Withdraw',
					icon: 'x-circle',
					action: 'withdraw',
					condition: (item: any) => item.status === 'active'
				}
			]
		};
	});

	$: breadcrumbs = [
		{ label: 'Privacy', href: `${base}/privacy` },
		{ label: 'Consent Records', href: `${base}/privacy/consent-records` }
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
				{safeTranslate('Consent Records')}
			</h1>
			<p class="text-gray-600 dark:text-gray-400 mt-1">
				Manage data subject consent records and compliance
			</p>
		</div>
		<div class="flex gap-2">
			<a
				href={`${base}/privacy/consent-records/new`}
				class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
			>
				<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
				</svg>
				New Consent Record
			</a>
		</div>
	</div>

	<!-- Consent Overview Cards -->
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
								Active Consents
							</dt>
							<dd class="text-lg font-medium text-gray-900 dark:text-white">
								{data.consentRecords.filter((record: any) => record.status === 'active').length}
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
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
						</svg>
					</div>
					<div class="ml-5 w-0 flex-1">
						<dl>
							<dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
								Withdrawn
							</dt>
							<dd class="text-lg font-medium text-gray-900 dark:text-white">
								{data.consentRecords.filter((record: any) => record.status === 'withdrawn').length}
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
						<svg class="h-6 w-6 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					</div>
					<div class="ml-5 w-0 flex-1">
						<dl>
							<dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
								Expired
							</dt>
							<dd class="text-lg font-medium text-gray-900 dark:text-white">
								{data.consentRecords.filter((record: any) => record.status === 'expired').length}
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
								Total Records
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

	<!-- Consent Records Table -->
	<div class="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
		{#if tableConfig}
			<ModelTable {tableConfig} />
		{:else}
			<div class="p-6 text-center">
				<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
				</svg>
				<h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">Loading consent records...</h3>
			</div>
		{/if}
	</div>
</div>
