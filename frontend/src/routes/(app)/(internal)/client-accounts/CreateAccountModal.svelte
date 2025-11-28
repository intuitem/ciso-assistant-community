<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';

	interface Props {
		form: any;
	}

	let { form }: Props = $props();

	const modalStore = getModalStore();

	let loading = $state(false);

	function closeModal() {
		modalStore.close();
	}

	function handleSubmit() {
		loading = true;
		return async ({ result, update }) => {
			loading = false;
			if (result.type === 'success' || result.type === 'redirect') {
				closeModal();
				await invalidateAll();
			} else {
				await update();
			}
		};
	}
</script>

<div class="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
	<form method="POST" action="?/create" use:enhance={handleSubmit} class="space-y-6">
		<!-- Company Information -->
		<div class="space-y-4">
			<h3 class="text-lg font-medium text-gray-900 border-b pb-2">Company Information</h3>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label for="name" class="block text-sm font-medium text-gray-700">Company Name *</label>
					<input
						type="text"
						id="name"
						name="name"
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
						placeholder="Acme Corporation"
					/>
				</div>

				<div>
					<label for="slug" class="block text-sm font-medium text-gray-700">Slug (optional)</label>
					<input
						type="text"
						id="slug"
						name="slug"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
						placeholder="acme-corp"
					/>
					<p class="mt-1 text-xs text-gray-500">Auto-generated if left empty</p>
				</div>

				<div>
					<label for="email" class="block text-sm font-medium text-gray-700">Contact Email *</label>
					<input
						type="email"
						id="email"
						name="email"
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
						placeholder="contact@acme.com"
					/>
				</div>

				<div>
					<label for="phone" class="block text-sm font-medium text-gray-700">Phone (optional)</label
					>
					<input
						type="tel"
						id="phone"
						name="phone"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
						placeholder="+1 234 567 8900"
					/>
				</div>
			</div>

			<div>
				<label for="address" class="block text-sm font-medium text-gray-700">Address (optional)</label
				>
				<textarea
					id="address"
					name="address"
					rows="2"
					class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
					placeholder="123 Business St, City, Country"
				></textarea>
			</div>
		</div>

		<!-- Subscription Details -->
		<div class="space-y-4">
			<h3 class="text-lg font-medium text-gray-900 border-b pb-2">Subscription Details</h3>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label for="status" class="block text-sm font-medium text-gray-700">Status</label>
					<select
						id="status"
						name="status"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
					>
						<option value="trial">Trial</option>
						<option value="active">Active</option>
						<option value="suspended">Suspended</option>
					</select>
				</div>

				<div>
					<label for="plan" class="block text-sm font-medium text-gray-700">Plan</label>
					<select
						id="plan"
						name="plan"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
					>
						<option value="free">Free</option>
						<option value="basic">Basic</option>
						<option value="pro">Professional</option>
						<option value="enterprise">Enterprise</option>
					</select>
				</div>

				<div>
					<label for="subscription_start" class="block text-sm font-medium text-gray-700"
						>Start Date</label
					>
					<input
						type="date"
						id="subscription_start"
						name="subscription_start"
						value={new Date().toISOString().split('T')[0]}
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
					/>
				</div>

				<div>
					<label for="subscription_end" class="block text-sm font-medium text-gray-700"
						>End Date *</label
					>
					<input
						type="date"
						id="subscription_end"
						name="subscription_end"
						required
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
					/>
				</div>

				<div>
					<label for="max_users" class="block text-sm font-medium text-gray-700">Max Users</label>
					<input
						type="number"
						id="max_users"
						name="max_users"
						min="1"
						value="5"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
					/>
				</div>

				<div>
					<label for="max_domains" class="block text-sm font-medium text-gray-700">Max Domains</label
					>
					<input
						type="number"
						id="max_domains"
						name="max_domains"
						min="1"
						value="1"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
					/>
				</div>
			</div>
		</div>

		<!-- Admin User (Optional) -->
		<div class="space-y-4">
			<h3 class="text-lg font-medium text-gray-900 border-b pb-2">
				Admin User <span class="text-sm font-normal text-gray-500">(Optional)</span>
			</h3>
			<p class="text-sm text-gray-500">Create an admin user for this account</p>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div>
					<label for="admin_email" class="block text-sm font-medium text-gray-700">Admin Email</label
					>
					<input
						type="email"
						id="admin_email"
						name="admin_email"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
						placeholder="admin@acme.com"
					/>
				</div>

				<div>
					<label for="admin_first_name" class="block text-sm font-medium text-gray-700"
						>First Name</label
					>
					<input
						type="text"
						id="admin_first_name"
						name="admin_first_name"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
						placeholder="John"
					/>
				</div>

				<div>
					<label for="admin_last_name" class="block text-sm font-medium text-gray-700"
						>Last Name</label
					>
					<input
						type="text"
						id="admin_last_name"
						name="admin_last_name"
						class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
						placeholder="Doe"
					/>
				</div>
			</div>
		</div>

		<!-- Notes -->
		<div>
			<label for="notes" class="block text-sm font-medium text-gray-700">Notes (internal)</label>
			<textarea
				id="notes"
				name="notes"
				rows="3"
				class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
				placeholder="Internal notes about this account..."
			></textarea>
		</div>

		<!-- Actions -->
		<div class="flex justify-end gap-3 pt-4 border-t">
			<button
				type="button"
				onclick={closeModal}
				class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
			>
				Cancel
			</button>
			<button
				type="submit"
				disabled={loading}
				class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
			>
				{#if loading}
					<i class="fa-solid fa-spinner fa-spin"></i>
				{/if}
				Create Account
			</button>
		</div>
	</form>
</div>
