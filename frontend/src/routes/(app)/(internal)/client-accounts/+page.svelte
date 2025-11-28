<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';
	import type { ActionData, PageData } from './$types';
	import CreateAccountModal from './CreateAccountModal.svelte';
	import ExtendSubscriptionModal from './ExtendSubscriptionModal.svelte';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	// Status badge colors
	const statusColors: Record<string, string> = {
		active: 'bg-green-100 text-green-800 border-green-200',
		suspended: 'bg-red-100 text-red-800 border-red-200',
		expired: 'bg-gray-100 text-gray-800 border-gray-200',
		trial: 'bg-blue-100 text-blue-800 border-blue-200'
	};

	// Plan badge colors
	const planColors: Record<string, string> = {
		free: 'bg-gray-100 text-gray-700',
		basic: 'bg-blue-100 text-blue-700',
		pro: 'bg-purple-100 text-purple-700',
		enterprise: 'bg-amber-100 text-amber-700'
	};

	function openCreateModal() {
		const modalComponent: ModalComponent = {
			ref: CreateAccountModal,
			props: {
				form: data.createForm
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: 'Create New Account'
		};
		modalStore.trigger(modal);
	}

	function openExtendModal(accountId: string, accountName: string) {
		const modalComponent: ModalComponent = {
			ref: ExtendSubscriptionModal,
			props: {
				accountId,
				accountName
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: `Extend Subscription - ${accountName}`
		};
		modalStore.trigger(modal);
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getDaysText(days: number): string {
		if (days < 0) return 'Expired';
		if (days === 0) return 'Expires today';
		if (days === 1) return '1 day left';
		return `${days} days left`;
	}

	function getDaysColor(days: number): string {
		if (days < 0) return 'text-red-600';
		if (days <= 7) return 'text-orange-600';
		if (days <= 30) return 'text-yellow-600';
		return 'text-green-600';
	}
</script>

<div class="space-y-6">
	<!-- Stats Cards -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<div class="bg-white rounded-lg shadow p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-500">Total Accounts</p>
					<p class="text-3xl font-bold text-gray-900">{data.stats.total_accounts}</p>
				</div>
				<div class="p-3 bg-violet-100 rounded-full">
					<i class="fa-solid fa-building text-violet-600 text-xl"></i>
				</div>
			</div>
		</div>

		<div class="bg-white rounded-lg shadow p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-500">Active Accounts</p>
					<p class="text-3xl font-bold text-green-600">{data.stats.active_accounts}</p>
				</div>
				<div class="p-3 bg-green-100 rounded-full">
					<i class="fa-solid fa-check-circle text-green-600 text-xl"></i>
				</div>
			</div>
		</div>

		<div class="bg-white rounded-lg shadow p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-500">Expiring Soon</p>
					<p class="text-3xl font-bold text-orange-600">{data.stats.expiring_soon}</p>
				</div>
				<div class="p-3 bg-orange-100 rounded-full">
					<i class="fa-solid fa-clock text-orange-600 text-xl"></i>
				</div>
			</div>
		</div>

		<div class="bg-white rounded-lg shadow p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-500">Total Users</p>
					<p class="text-3xl font-bold text-blue-600">{data.stats.total_users}</p>
				</div>
				<div class="p-3 bg-blue-100 rounded-full">
					<i class="fa-solid fa-users text-blue-600 text-xl"></i>
				</div>
			</div>
		</div>
	</div>

	<!-- Filters and Actions -->
	<div class="bg-white rounded-lg shadow p-4">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div class="flex flex-wrap items-center gap-3">
				<!-- Search -->
				<form method="GET" class="flex items-center">
					<input
						type="text"
						name="search"
						placeholder="Search accounts..."
						value={$page.url.searchParams.get('search') || ''}
						class="px-4 py-2 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
					/>
					<button
						type="submit"
						class="px-4 py-2 bg-violet-500 text-white rounded-r-lg hover:bg-violet-600"
					>
						<i class="fa-solid fa-search"></i>
					</button>
				</form>

				<!-- Status Filter -->
				<select
					onchange={(e) => {
						const url = new URL($page.url);
						url.searchParams.set('status', e.currentTarget.value);
						window.location.href = url.toString();
					}}
					class="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
				>
					<option value="">All Status</option>
					<option value="active" selected={$page.url.searchParams.get('status') === 'active'}
						>Active</option
					>
					<option value="trial" selected={$page.url.searchParams.get('status') === 'trial'}
						>Trial</option
					>
					<option value="suspended" selected={$page.url.searchParams.get('status') === 'suspended'}
						>Suspended</option
					>
					<option value="expired" selected={$page.url.searchParams.get('status') === 'expired'}
						>Expired</option
					>
				</select>

				<!-- Plan Filter -->
				<select
					onchange={(e) => {
						const url = new URL($page.url);
						url.searchParams.set('plan', e.currentTarget.value);
						window.location.href = url.toString();
					}}
					class="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
				>
					<option value="">All Plans</option>
					<option value="free" selected={$page.url.searchParams.get('plan') === 'free'}>Free</option>
					<option value="basic" selected={$page.url.searchParams.get('plan') === 'basic'}
						>Basic</option
					>
					<option value="pro" selected={$page.url.searchParams.get('plan') === 'pro'}>Pro</option>
					<option value="enterprise" selected={$page.url.searchParams.get('plan') === 'enterprise'}
						>Enterprise</option
					>
				</select>
			</div>

			<button
				onclick={openCreateModal}
				class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 flex items-center gap-2"
			>
				<i class="fa-solid fa-plus"></i>
				New Account
			</button>
		</div>
	</div>

	<!-- Accounts Table -->
	<div class="bg-white rounded-lg shadow overflow-hidden">
		<table class="min-w-full divide-y divide-gray-200">
			<thead class="bg-gray-50">
				<tr>
					<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>Company</th
					>
					<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>Contact</th
					>
					<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>Status</th
					>
					<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>Plan</th
					>
					<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>Users</th
					>
					<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>Subscription</th
					>
					<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>Actions</th
					>
				</tr>
			</thead>
			<tbody class="bg-white divide-y divide-gray-200">
				{#each data.accounts as account}
					<tr class="hover:bg-gray-50">
						<td class="px-6 py-4 whitespace-nowrap">
							<div class="flex items-center">
								<div>
									<div class="text-sm font-medium text-gray-900">{account.name}</div>
									<div class="text-sm text-gray-500">{account.slug}</div>
								</div>
							</div>
						</td>
						<td class="px-6 py-4 whitespace-nowrap">
							<div class="text-sm text-gray-900">{account.email}</div>
						</td>
						<td class="px-6 py-4 whitespace-nowrap">
							<span
								class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border {statusColors[
									account.status
								]}"
							>
								{account.status}
							</span>
						</td>
						<td class="px-6 py-4 whitespace-nowrap">
							<span
								class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-md {planColors[
									account.plan
								]}"
							>
								{account.plan}
							</span>
						</td>
						<td class="px-6 py-4 whitespace-nowrap">
							<div class="text-sm text-gray-900">
								{account.user_count} / {account.max_users}
							</div>
							{#if account.user_count >= account.max_users}
								<div class="text-xs text-red-500">Limit reached</div>
							{/if}
						</td>
						<td class="px-6 py-4 whitespace-nowrap">
							<div class="text-sm text-gray-900">{formatDate(account.subscription_end)}</div>
							<div class="text-xs {getDaysColor(account.days_until_expiry)}">
								{getDaysText(account.days_until_expiry)}
							</div>
						</td>
						<td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
							<div class="flex items-center gap-2">
								<a
									href="/client-accounts/{account.id}"
									class="text-violet-600 hover:text-violet-900"
									title="View Details"
								>
									<i class="fa-solid fa-eye"></i>
								</a>

								{#if account.status !== 'active'}
									<form method="POST" action="?/activate" use:enhance>
										<input type="hidden" name="id" value={account.id} />
										<button
											type="submit"
											class="text-green-600 hover:text-green-900"
											title="Activate"
										>
											<i class="fa-solid fa-play"></i>
										</button>
									</form>
								{/if}

								{#if account.status === 'active' || account.status === 'trial'}
									<form method="POST" action="?/suspend" use:enhance>
										<input type="hidden" name="id" value={account.id} />
										<button type="submit" class="text-red-600 hover:text-red-900" title="Suspend">
											<i class="fa-solid fa-pause"></i>
										</button>
									</form>
								{/if}

								<button
									onclick={() => openExtendModal(account.id, account.name)}
									class="text-blue-600 hover:text-blue-900"
									title="Extend Subscription"
								>
									<i class="fa-solid fa-calendar-plus"></i>
								</button>

								<form
									method="POST"
									action="?/delete"
									use:enhance
									onsubmit={(e) => {
										if (
											!confirm(`Are you sure you want to delete ${account.name}? This cannot be undone.`)
										) {
											e.preventDefault();
										}
									}}
								>
									<input type="hidden" name="id" value={account.id} />
									<button type="submit" class="text-red-600 hover:text-red-900" title="Delete">
										<i class="fa-solid fa-trash"></i>
									</button>
								</form>
							</div>
						</td>
					</tr>
				{:else}
					<tr>
						<td colspan="7" class="px-6 py-12 text-center text-gray-500">
							<i class="fa-solid fa-building text-4xl mb-4 opacity-50"></i>
							<p>No accounts found</p>
							<button
								onclick={openCreateModal}
								class="mt-4 text-violet-600 hover:text-violet-800 font-medium"
							>
								Create your first account
							</button>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
