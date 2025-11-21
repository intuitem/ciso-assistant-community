<script lang="ts">
	import { goto } from '$app/navigation';
	import { enhance } from '$app/forms';
	import * as m from '$paraglide/messages.js';
	import { getToastStore } from '$lib/components/Toast/stores';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
		form: any;
	}

	let { data, form }: Props = $props();

	const toastStore = getToastStore();

	let assetsText = $state('');
	let selectedFolderId = $state('');

	// Check if form has been submitted and handle the result
	let formSubmitted = $derived(form !== null && form !== undefined);

	$effect(() => {
		if (form?.success) {
			toastStore.trigger({
				message: `Successfully created ${form.created} asset(s)`
			});

			if (form.errors.length === 0) {
				assetsText = '';
				selectedFolderId = '';
			}
		} else if (form?.error) {
			toastStore.trigger({
				message: form.error
			});
		}
	});

	function handleCancel() {
		goto('/experimental');
	}
</script>

<div class="grid grid-cols-4 gap-4">
	<div class="col-span-2 bg-white shadow-sm py-4 px-6 space-y-2">
		<div>
			<h4 class="h4 font-bold">
				<i class="fa-solid fa-layer-group mr-2"></i>Batch Asset Creation
			</h4>
			<p class="text-sm">Create multiple assets at once by entering them in the text area below.</p>
		</div>

		<div class="py-4">
			<ol class="list-decimal list-inside space-y-1 text-sm">
				<li>Select the target folder</li>
				<li>Enter asset names (one per line)</li>
				<li>Use SP: prefix for Support assets (default)</li>
				<li>Use PR: prefix for Primary assets</li>
				<li>Click Create Assets</li>
			</ol>
		</div>

		<form method="post" use:enhance class="space-y-4">
			<div class="rounded-lg p-4 border-2 border-green-500">
				<label for="folder" class="block text-sm font-medium text-gray-900">
					Target Folder *
				</label>
				<select
					id="folder"
					name="folder"
					bind:value={selectedFolderId}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
					required
				>
					<option value="">Select a folder</option>
					{#each data.folders as folder}
						<option value={folder.id}>{folder.str || folder.name}</option>
					{/each}
				</select>
			</div>

			<div class="rounded-lg p-4 border-2 border-pink-500">
				<label for="assets" class="block text-sm font-medium text-gray-900">
					Assets List *
				</label>
				<textarea
					id="assets"
					name="assets_text"
					bind:value={assetsText}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
					rows="15"
					placeholder="Enter asset names, one per line&#10;Example:&#10;Web Server&#10;SP:Database Server&#10;PR:Customer Database"
					required
				></textarea>
				<p class="text-sm mt-1">
					{assetsText.split('\n').filter((line) => line.trim()).length} asset(s) to create
				</p>
			</div>

			<div class="flex gap-2">
				<button
					type="submit"
					class="btn preset-filled"
				>
					<i class="fa-solid fa-plus mr-2"></i>
					Create Assets
				</button>
				<button
					type="button"
					onclick={handleCancel}
					class="btn"
				>
					Cancel
				</button>
			</div>
		</form>
	</div>

	<div class="col-span-2 p-4">
		<h4 class="font-semibold mb-2">Results</h4>
		{#if formSubmitted}
			{#if form?.success}
				<div class="alert alert-success preset-filled-success-500 mb-4">
					<div>Successfully created {form.created} asset(s)</div>
				</div>
				{#if form.assets && form.assets.length > 0}
					<div class="space-y-1 mb-4">
						{#each form.assets as asset}
							<div class="text-sm">
								<a href="/assets/{asset.id}" class="text-indigo-600 hover:text-indigo-400">
									{asset.name}
								</a>
								<span class="text-gray-500">({asset.type})</span>
							</div>
						{/each}
					</div>
				{/if}

				{#if form.errors && form.errors.length > 0}
					<div class="alert alert-error preset-filled-error-500 mb-4">
						<div>Errors: {form.errors.length}</div>
					</div>
					<div class="space-y-2">
						{#each form.errors as error}
							<div class="text-sm p-2 bg-gray-50 rounded">
								<span class="font-mono">{error.line}</span>
								<span class="text-red-600">
									- {JSON.stringify(error.errors || error.error)}
								</span>
							</div>
						{/each}
					</div>
				{/if}
			{:else}
				<div class="alert alert-error preset-filled-error-500 mb-4">
					<div>{form?.error || 'An error occurred'}</div>
				</div>
			{/if}
		{:else}
			<p class="text-sm text-gray-500">Results will appear here after submission</p>
		{/if}
	</div>
</div>
