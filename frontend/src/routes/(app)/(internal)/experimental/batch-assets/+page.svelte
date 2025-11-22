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
			const messages = [];
			if (form.created > 0) {
				messages.push(`Created ${form.created} asset(s)`);
			}
			if (form.reused > 0) {
				messages.push(`Reused ${form.reused} existing asset(s)`);
			}
			if (form.errors && form.errors.length > 0) {
				messages.push(`${form.errors.length} error(s)`);
			}
			toastStore.trigger({
				message: messages.join(', ')
			});

			// Only clear form if there are no errors
			if (!form.errors || form.errors.length === 0) {
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
				<i class="fa-solid fa-layer-group mr-2"></i>Scratchpad: batch Assets creation
			</h4>
			<p class="text-sm">Create multiple assets at once by entering them in the text area below.</p>
		</div>

		<div class="py-4">
			<h5 class="font-semibold mb-2 text-sm">Instructions:</h5>
			<ol class="list-decimal list-inside space-y-1 text-sm">
				<li>Select the target folder</li>
				<li>Enter asset names (one per line)</li>
				<li>Use SP: prefix for Support assets (default)</li>
				<li>Use PR: prefix for Primary assets</li>
				<li>Indent with 2 spaces per level to create parent-child relationships</li>
				<li>Click Create Assets</li>
			</ol>
			<div class="mt-3 p-3 bg-gray-50 rounded text-xs space-y-2">
				<div>
					<p class="font-semibold mb-1">Example with multi-level hierarchy:</p>
					<pre class="font-mono">PR:Customer Database
  SP:User Data
    SP:Login Data
    SP:Profile Data
  SP:Payment Data
Web Application
  SP:API Gateway
  SP:Load Balancer</pre>
				</div>
				<div class="pt-2 border-t border-gray-200">
					<p class="font-semibold mb-1">Note:</p>
					<ul class="list-disc list-inside space-y-1">
						<li>Assets with the same name in the folder will be reused</li>
						<li>Errors won't stop the batch process</li>
					</ul>
				</div>
			</div>
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
				<label for="assets" class="block text-sm font-medium text-gray-900"> Assets List * </label>
				<textarea
					id="assets"
					name="assets_text"
					bind:value={assetsText}
					class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm font-mono"
					rows="15"
					required
				></textarea>
				<p class="text-sm mt-1">
					{assetsText.split('\n').filter((line) => line.trim()).length} asset(s) to create
				</p>
			</div>

			<div class="flex gap-2">
				<button type="submit" class="btn preset-filled">
					<i class="fa-solid fa-plus mr-2"></i>
					Create Assets
				</button>
				<button type="button" onclick={handleCancel} class="btn"> Cancel </button>
			</div>
		</form>
	</div>

	<div class="col-span-2 p-4">
		<h4 class="font-semibold mb-2">Results</h4>
		{#if formSubmitted}
			{#if form?.success}
				<div class="alert alert-success preset-filled-success-500 mb-4">
					<div>
						{#if form.created > 0}Created {form.created} asset(s){/if}
						{#if form.created > 0 && form.reused > 0},
						{/if}
						{#if form.reused > 0}Reused {form.reused} existing asset(s){/if}
					</div>
				</div>

				{#if form.assets && form.assets.length > 0}
					<div class="mb-4">
						<h5 class="font-semibold text-sm mb-2 text-green-600">Created Assets:</h5>
						<div class="space-y-1">
							{#each form.assets as asset}
								<div class="text-sm">
									<a href="/assets/{asset.id}" class="text-indigo-600 hover:text-indigo-400">
										{asset.name}
									</a>
									<span class="text-gray-500">({asset.type})</span>
									{#if asset.parent}
										<span class="text-gray-400 text-xs">→ child of {asset.parent}</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if form.reused_assets && form.reused_assets.length > 0}
					<div class="mb-4">
						<h5 class="font-semibold text-sm mb-2 text-blue-600">Reused Existing Assets:</h5>
						<div class="space-y-1">
							{#each form.reused_assets as asset}
								<div class="text-sm">
									<a href="/assets/{asset.id}" class="text-indigo-600 hover:text-indigo-400">
										{asset.name}
									</a>
									<span class="text-gray-500">({asset.type})</span>
									{#if asset.parent}
										<span class="text-gray-400 text-xs">→ child of {asset.parent}</span>
									{/if}
								</div>
							{/each}
						</div>
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
