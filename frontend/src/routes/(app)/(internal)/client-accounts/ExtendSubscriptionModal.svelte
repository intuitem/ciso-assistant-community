<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { getModalStore } from '$lib/components/Modals/stores';

	interface Props {
		accountId: string;
		accountName: string;
	}

	let { accountId, accountName }: Props = $props();

	const modalStore = getModalStore();

	let loading = $state(false);
	let days = $state(30);

	const presetDays = [
		{ label: '7 days', value: 7 },
		{ label: '14 days', value: 14 },
		{ label: '30 days', value: 30 },
		{ label: '90 days', value: 90 },
		{ label: '180 days', value: 180 },
		{ label: '365 days', value: 365 }
	];

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

<div class="p-6 space-y-6">
	<p class="text-gray-600">
		Extend the subscription for <strong>{accountName}</strong> by selecting the number of days below.
	</p>

	<form method="POST" action="?/extend" use:enhance={handleSubmit} class="space-y-6">
		<input type="hidden" name="id" value={accountId} />

		<!-- Preset buttons -->
		<div class="flex flex-wrap gap-2">
			{#each presetDays as preset}
				<button
					type="button"
					onclick={() => (days = preset.value)}
					class="px-3 py-1 rounded-lg border transition-colors {days === preset.value
						? 'bg-violet-600 text-white border-violet-600'
						: 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}"
				>
					{preset.label}
				</button>
			{/each}
		</div>

		<!-- Custom days input -->
		<div>
			<label for="days" class="block text-sm font-medium text-gray-700">Days to extend</label>
			<div class="mt-1 flex items-center gap-3">
				<input
					type="number"
					id="days"
					name="days"
					min="1"
					max="3650"
					bind:value={days}
					class="block w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-violet-500 focus:border-violet-500"
				/>
				<span class="text-gray-500">days</span>
			</div>
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
				disabled={loading || days < 1}
				class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
			>
				{#if loading}
					<i class="fa-solid fa-spinner fa-spin"></i>
				{/if}
				Extend by {days} days
			</button>
		</div>
	</form>
</div>
