<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import type { ActionData, PageData } from './$types';
	import ExtendSubscriptionModal from '../ExtendSubscriptionModal.svelte';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	let editing = $state(false);
	let loading = $state(false);

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

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	function formatDateTime(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getDaysText(days: number): string {
		if (days < 0) return `Expired ${Math.abs(days)} days ago`;
		if (days === 0) return 'Expires today';
		if (days === 1) return '1 day remaining';
		return `${days} days remaining`;
	}

	function getDaysColor(days: number): string {
		if (days < 0) return 'text-red-600 bg-red-50';
		if (days <= 7) return 'text-orange-600 bg-orange-50';
		if (days <= 30) return 'text-yellow-600 bg-yellow-50';
		return 'text-green-600 bg-green-50';
	}

	function openExtendModal() {
		const modalComponent: ModalComponent = {
			ref: ExtendSubscriptionModal,
			props: {
				accountId: data.account.id,
				accountName: data.account.name
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: `Extend Subscription - ${data.account.name}`
		};
		modalStore.trigger(modal);
	}

	function handleSubmit() {
		loading = true;
		return async ({ result, update }) => {
			loading = false;
			editing = false;
			await update();
			await invalidateAll();
		};
	}
</script>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-4">
			<a href="/client-accounts" class="text-gray-500 hover:text-gray-700">
				<i class="fa-solid fa-arrow-left text-xl"></i>
			</a>
			<div>
				<h1 class="text-2xl font-bold text-gray-900">{data.account.name}</h1>
				<p class="text-sm text-gray-500">{data.account.slug}</p>
			</div>
		</div>

		<div class="flex items-center gap-3">
			{#if data.account.status !== 'active'}
				<form method="POST" action="?/activate" use:enhance>
					<button
						type="submit"
						class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
					>
						<i class="fa-solid fa-play"></i>
						Activate
					</button>
				</form>
			{/if}

			{#if data.account.status === 'active' || data.account.status === 'trial'}
				<form method="POST" action="?/suspend" use:enhance>
					<button
						type="submit"
						class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
					>
						<i class="fa-solid fa-pause"></i>
						Suspend
					</button>
				</form>
			{/if}

			<button
				onclick={openExtendModal}
				class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
			>
				<i class="fa-solid fa-calendar-plus"></i>
				Extend
			</button>

			<button
				onclick={() => (editing = !editing)}
				class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 flex items-center gap-2"
			>
				<i class="fa-solid {editing ? 'fa-times' : 'fa-edit'}"></i>
				{editing ? 'Cancel' : 'Edit'}
			</button>
		</div>
	</div>

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Main Info -->
		<div class="lg:col-span-2 space-y-6">
			<!-- Account Details Card -->
			<div class="bg-white rounded-lg shadow p-6">
				<h2 class="text-lg font-semibold text-gray-900 mb-4">Account Details</h2>

				{#if editing}
					<form method="POST" action="?/update" use:enhance={handleSubmit} class="space-y-4">
						<div class="grid grid-cols-2 gap-4">
							<div>
								<label for="name" class="block text-sm font-medium text-gray-700"
									>Company Name</label
								>
								<input
									type="text"
									id="name"
									name="name"
									value={data.account.name}
									required
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								/>
							</div>

							<div>
								<label for="email" class="block text-sm font-medium text-gray-700"
									>Contact Email</label
								>
								<input
									type="email"
									id="email"
									name="email"
									value={data.account.email}
									required
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								/>
							</div>

							<div>
								<label for="phone" class="block text-sm font-medium text-gray-700">Phone</label>
								<input
									type="tel"
									id="phone"
									name="phone"
									value={data.account.phone || ''}
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								/>
							</div>

							<div>
								<label for="status" class="block text-sm font-medium text-gray-700">Status</label>
								<select
									id="status"
									name="status"
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								>
									<option value="trial" selected={data.account.status === 'trial'}>Trial</option>
									<option value="active" selected={data.account.status === 'active'}>Active</option>
									<option value="suspended" selected={data.account.status === 'suspended'}
										>Suspended</option
									>
									<option value="expired" selected={data.account.status === 'expired'}
										>Expired</option
									>
								</select>
							</div>

							<div>
								<label for="plan" class="block text-sm font-medium text-gray-700">Plan</label>
								<select
									id="plan"
									name="plan"
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								>
									<option value="free" selected={data.account.plan === 'free'}>Free</option>
									<option value="basic" selected={data.account.plan === 'basic'}>Basic</option>
									<option value="pro" selected={data.account.plan === 'pro'}>Professional</option>
									<option value="enterprise" selected={data.account.plan === 'enterprise'}
										>Enterprise</option
									>
								</select>
							</div>

							<div>
								<label for="subscription_end" class="block text-sm font-medium text-gray-700"
									>Subscription End</label
								>
								<input
									type="date"
									id="subscription_end"
									name="subscription_end"
									value={data.account.subscription_end}
									required
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								/>
							</div>

							<div>
								<label for="max_users" class="block text-sm font-medium text-gray-700"
									>Max Users</label
								>
								<input
									type="number"
									id="max_users"
									name="max_users"
									min="1"
									value={data.account.max_users}
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								/>
							</div>

							<div>
								<label for="max_domains" class="block text-sm font-medium text-gray-700"
									>Max Domains</label
								>
								<input
									type="number"
									id="max_domains"
									name="max_domains"
									min="1"
									value={data.account.max_domains}
									class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								/>
							</div>
						</div>

						<div>
							<label for="address" class="block text-sm font-medium text-gray-700">Address</label>
							<textarea
								id="address"
								name="address"
								rows="2"
								class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								>{data.account.address || ''}</textarea
							>
						</div>

						<div>
							<label for="notes" class="block text-sm font-medium text-gray-700">Notes</label>
							<textarea
								id="notes"
								name="notes"
								rows="3"
								class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
								>{data.account.notes || ''}</textarea
							>
						</div>

						<div class="flex justify-end">
							<button
								type="submit"
								disabled={loading}
								class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50"
							>
								{#if loading}
									<i class="fa-solid fa-spinner fa-spin mr-2"></i>
								{/if}
								Save Changes
							</button>
						</div>
					</form>
				{:else}
					<dl class="grid grid-cols-2 gap-x-4 gap-y-4">
						<div>
							<dt class="text-sm font-medium text-gray-500">Contact Email</dt>
							<dd class="mt-1 text-sm text-gray-900">{data.account.email}</dd>
						</div>
						<div>
							<dt class="text-sm font-medium text-gray-500">Phone</dt>
							<dd class="mt-1 text-sm text-gray-900">{data.account.phone || '-'}</dd>
						</div>
						<div class="col-span-2">
							<dt class="text-sm font-medium text-gray-500">Address</dt>
							<dd class="mt-1 text-sm text-gray-900">{data.account.address || '-'}</dd>
						</div>
						<div>
							<dt class="text-sm font-medium text-gray-500">Created</dt>
							<dd class="mt-1 text-sm text-gray-900">{formatDateTime(data.account.created_at)}</dd>
						</div>
						<div>
							<dt class="text-sm font-medium text-gray-500">Last Updated</dt>
							<dd class="mt-1 text-sm text-gray-900">{formatDateTime(data.account.updated_at)}</dd>
						</div>
						{#if data.account.notes}
							<div class="col-span-2">
								<dt class="text-sm font-medium text-gray-500">Notes</dt>
								<dd class="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{data.account.notes}</dd>
							</div>
						{/if}
					</dl>
				{/if}
			</div>

			<!-- Users Card -->
			<div class="bg-white rounded-lg shadow p-6">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold text-gray-900">
						Users ({data.users.length}/{data.account.max_users})
					</h2>
				</div>

				{#if data.users.length > 0}
					<table class="min-w-full divide-y divide-gray-200">
						<thead class="bg-gray-50">
							<tr>
								<th
									class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
									>User</th
								>
								<th
									class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
									>Status</th
								>
								<th
									class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
									>Joined</th
								>
								<th
									class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
									>Last Login</th
								>
							</tr>
						</thead>
						<tbody class="bg-white divide-y divide-gray-200">
							{#each data.users as user}
								<tr>
									<td class="px-4 py-3 whitespace-nowrap">
										<div class="text-sm font-medium text-gray-900">
											{user.first_name || ''} {user.last_name || ''}
										</div>
										<div class="text-sm text-gray-500">{user.email}</div>
									</td>
									<td class="px-4 py-3 whitespace-nowrap">
										<span
											class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full {user.is_active
												? 'bg-green-100 text-green-800'
												: 'bg-red-100 text-red-800'}"
										>
											{user.is_active ? 'Active' : 'Inactive'}
										</span>
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
										{formatDateTime(user.date_joined)}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
										{formatDateTime(user.last_login)}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<div class="text-center py-8 text-gray-500">
						<i class="fa-solid fa-users text-4xl mb-2 opacity-50"></i>
						<p>No users in this account yet</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="space-y-6">
			<!-- Status Card -->
			<div class="bg-white rounded-lg shadow p-6">
				<h3 class="text-sm font-medium text-gray-500 mb-3">Status</h3>
				<span
					class="px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full border {statusColors[
						data.account.status
					]}"
				>
					{data.account.status}
				</span>
			</div>

			<!-- Plan Card -->
			<div class="bg-white rounded-lg shadow p-6">
				<h3 class="text-sm font-medium text-gray-500 mb-3">Plan</h3>
				<span
					class="px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-md {planColors[
						data.account.plan
					]}"
				>
					{data.account.plan}
				</span>
			</div>

			<!-- Subscription Card -->
			<div class="bg-white rounded-lg shadow p-6">
				<h3 class="text-sm font-medium text-gray-500 mb-3">Subscription</h3>
				<div class="space-y-2">
					<div class="flex justify-between text-sm">
						<span class="text-gray-500">Start</span>
						<span class="text-gray-900">{formatDate(data.account.subscription_start)}</span>
					</div>
					<div class="flex justify-between text-sm">
						<span class="text-gray-500">End</span>
						<span class="text-gray-900">{formatDate(data.account.subscription_end)}</span>
					</div>
					<div
						class="mt-3 px-3 py-2 rounded-lg text-center font-medium {getDaysColor(
							data.account.days_until_expiry
						)}"
					>
						{getDaysText(data.account.days_until_expiry)}
					</div>
				</div>
			</div>

			<!-- Limits Card -->
			<div class="bg-white rounded-lg shadow p-6">
				<h3 class="text-sm font-medium text-gray-500 mb-3">Limits</h3>
				<div class="space-y-3">
					<div>
						<div class="flex justify-between text-sm mb-1">
							<span class="text-gray-500">Users</span>
							<span class="text-gray-900">{data.account.user_count} / {data.account.max_users}</span
							>
						</div>
						<div class="w-full bg-gray-200 rounded-full h-2">
							<div
								class="h-2 rounded-full {data.account.user_count >= data.account.max_users
									? 'bg-red-500'
									: 'bg-violet-500'}"
								style="width: {Math.min(
									(data.account.user_count / data.account.max_users) * 100,
									100
								)}%"
							></div>
						</div>
					</div>
					<div>
						<div class="flex justify-between text-sm">
							<span class="text-gray-500">Max Domains</span>
							<span class="text-gray-900">{data.account.max_domains}</span>
						</div>
					</div>
				</div>
			</div>

			<!-- Domain Folder Card -->
			{#if data.account.folder_id}
				<div class="bg-white rounded-lg shadow p-6">
					<h3 class="text-sm font-medium text-gray-500 mb-3">Domain Folder</h3>
					<div class="text-sm">
						<div class="font-medium text-gray-900">{data.account.folder_name}</div>
						<div class="text-gray-500 text-xs font-mono mt-1">{data.account.folder_id}</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
