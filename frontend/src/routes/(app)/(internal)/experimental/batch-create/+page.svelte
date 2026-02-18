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

	type BatchType = 'assets' | 'entities' | 'feared-events';

	let selectedType = $state<BatchType>('assets');
	let itemsText = $state('');
	let selectedFolderId = $state('');
	let selectedStudyId = $state('');

	// Check if form has been submitted and handle the result
	let formSubmitted = $derived(form !== null && form !== undefined);

	// Type-specific labels
	const typeLabels = {
		assets: { singular: 'Asset', plural: 'Assets', icon: 'fa-layer-group' },
		entities: { singular: 'Entity', plural: 'Entities', icon: 'fa-building' },
		'feared-events': {
			singular: 'Feared Event',
			plural: 'Feared Events',
			icon: 'fa-exclamation-triangle'
		}
	};

	$effect(() => {
		if (form?.success) {
			const label = typeLabels[form.type || selectedType];
			const messages = [];
			if (form.created > 0) {
				messages.push(`Created ${form.created} ${label.plural.toLowerCase()}`);
			}
			if (form.skipped > 0) {
				messages.push(`Skipped ${form.skipped} existing ${label.plural.toLowerCase()}`);
			}
			if (form.errors && form.errors.length > 0) {
				messages.push(`${form.errors.length} error(s)`);
			}
			toastStore.trigger({
				message: messages.join(', ')
			});

			// Only clear form if there are no errors
			if (!form.errors || form.errors.length === 0) {
				itemsText = '';
				selectedFolderId = '';
				selectedStudyId = '';
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

	function handleTextareaKeydown(event: KeyboardEvent) {
		// Only enable Tab indentation for assets (which support hierarchy)
		if (selectedType === 'assets' && event.key === 'Tab') {
			event.preventDefault();
			const target = event.target as HTMLTextAreaElement;
			const start = target.selectionStart;
			const end = target.selectionEnd;

			// Insert 2 spaces (matching the indentation format in instructions)
			const indent = '  ';
			itemsText = itemsText.substring(0, start) + indent + itemsText.substring(end);

			// Move cursor after the inserted indentation
			requestAnimationFrame(() => {
				target.selectionStart = target.selectionEnd = start + indent.length;
			});
		}
	}

	function handleTypeChange() {
		// Reset form when changing type
		itemsText = '';
		selectedFolderId = '';
		selectedStudyId = '';
	}
</script>

<div class="grid grid-cols-4 gap-4">
	<div class="col-span-2 bg-surface-50-950 shadow-sm py-4 px-6 space-y-2">
		<div>
			<h4 class="h4 font-bold">
				<i class="fa-solid {typeLabels[selectedType].icon} mr-2"></i>Batch Creation
			</h4>
			<p class="text-sm">
				Create multiple {typeLabels[selectedType].plural.toLowerCase()} at once.
			</p>
		</div>

		<!-- Type Selector -->
		<div class="py-2">
			<label class="block text-sm font-medium text-surface-950-50 mb-2"> Type * </label>
			<div class="flex gap-2">
				<button
					type="button"
					class="btn {selectedType === 'assets' ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => {
						selectedType = 'assets';
						handleTypeChange();
					}}
				>
					<i class="fa-solid fa-layer-group mr-2"></i>Assets
				</button>
				<button
					type="button"
					class="btn {selectedType === 'entities' ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => {
						selectedType = 'entities';
						handleTypeChange();
					}}
				>
					<i class="fa-solid fa-building mr-2"></i>Entities
				</button>
				<button
					type="button"
					class="btn {selectedType === 'feared-events' ? 'preset-filled' : 'preset-outlined'}"
					onclick={() => {
						selectedType = 'feared-events';
						handleTypeChange();
					}}
				>
					<i class="fa-solid fa-exclamation-triangle mr-2"></i>Feared Events
				</button>
			</div>
		</div>

		<!-- Instructions -->
		<div class="py-2">
			<h5 class="font-semibold mb-2 text-sm">Instructions:</h5>
			{#if selectedType === 'assets'}
				<ol class="list-decimal list-inside space-y-1 text-sm">
					<li>Select the target folder</li>
					<li>Enter asset names (one per line)</li>
					<li>Use SP: prefix for Support assets (default)</li>
					<li>Use PR: prefix for Primary assets</li>
					<li>Indent with 2 spaces (tab works too) to create parent-child relationships</li>
					<li>Click Create</li>
				</ol>
				<div class="mt-3 p-3 bg-surface-50-950 rounded text-xs">
					<p class="font-semibold mb-1">Example:</p>
					<pre class="font-mono">PR:Customer Database
  SP:User Data
    SP:Login Data
Web Application</pre>
				</div>
			{:else if selectedType === 'entities'}
				<ol class="list-decimal list-inside space-y-1 text-sm">
					<li>Select the target folder</li>
					<li>Enter entity names (one per line)</li>
					<li>Optionally prefix with ref_id (REF-001:Entity Name)</li>
					<li>Click Create</li>
				</ol>
				<div class="mt-3 p-3 bg-surface-50-950 rounded text-xs">
					<p class="font-semibold mb-1">Example:</p>
					<pre class="font-mono">Vendor A
REF-002:Vendor B
Subsidiary C</pre>
				</div>
			{:else if selectedType === 'feared-events'}
				<ol class="list-decimal list-inside space-y-1 text-sm">
					<li>Select the EBIOS RM study</li>
					<li>Enter feared event names (one per line)</li>
					<li>Optionally prefix with ref_id (REF-001:Event Name)</li>
					<li>Click Create</li>
				</ol>
				<div class="mt-3 p-3 bg-surface-50-950 rounded text-xs">
					<p class="font-semibold mb-1">Example:</p>
					<pre class="font-mono">Data breach
REF-002:System outage
Loss of customer trust</pre>
				</div>
			{/if}
		</div>

		<!-- Form -->
		<form method="post" use:enhance class="space-y-4">
			<input type="hidden" name="type" value={selectedType} />

			<!-- Container selector (Folder or Study) -->
			{#if selectedType === 'assets' || selectedType === 'entities'}
				<div class="rounded-lg p-4 border-2 border-green-500">
					<label for="folder" class="block text-sm font-medium text-surface-950-50">
						Target Folder *
					</label>
					<select
						id="folder"
						name="folder"
						bind:value={selectedFolderId}
						class="mt-1.5 w-full rounded-lg border-surface-300-700 text-surface-700-300 sm:text-sm"
						required
					>
						<option value="">Select a folder</option>
						{#each data.folders as folder}
							<option value={folder.id}>{folder.str || folder.name}</option>
						{/each}
					</select>
				</div>
			{:else if selectedType === 'feared-events'}
				<div class="rounded-lg p-4 border-2 border-green-500">
					<label for="study" class="block text-sm font-medium text-surface-950-50">
						EBIOS RM Study *
					</label>
					<select
						id="study"
						name="study"
						bind:value={selectedStudyId}
						class="mt-1.5 w-full rounded-lg border-surface-300-700 text-surface-700-300 sm:text-sm"
						required
					>
						<option value="">Select a study</option>
						{#each data.studies as study}
							<option value={study.id}>{study.name}</option>
						{/each}
					</select>
				</div>
			{/if}

			<!-- Items textarea -->
			<div class="rounded-lg p-4 border-2 border-pink-500">
				<label for="items" class="block text-sm font-medium text-surface-950-50">
					{typeLabels[selectedType].plural} List *
				</label>
				<textarea
					id="items"
					name="items_text"
					bind:value={itemsText}
					onkeydown={handleTextareaKeydown}
					class="mt-1.5 w-full rounded-lg border-surface-300-700 text-surface-700-300 sm:text-sm font-mono"
					rows="15"
					required
				></textarea>
				<p class="text-sm mt-1">
					{itemsText.split('\n').filter((line) => line.trim()).length}
					{typeLabels[selectedType].plural.toLowerCase()} to create
				</p>
			</div>

			<!-- Buttons -->
			<div class="flex gap-2">
				<button type="submit" class="btn preset-filled">
					<i class="fa-solid fa-plus mr-2"></i>
					Create {typeLabels[selectedType].plural}
				</button>
				<button type="button" onclick={handleCancel} class="btn"> Cancel </button>
			</div>
		</form>
	</div>

	<div class="col-span-2 p-4">
		<h4 class="font-semibold mb-2">Results</h4>
		{#if formSubmitted}
			{#if form?.success}
				{@const formType = form.type || selectedType}
				{@const label = typeLabels[formType]}
				{@const routePath =
					formType === 'assets'
						? '/assets'
						: formType === 'entities'
							? '/entities'
							: '/feared-events'}

				<div class="alert alert-success preset-filled-success-500 mb-4">
					<div>
						{#if form.created > 0}Created {form.created} {label.plural.toLowerCase()}{/if}
						{#if form.created > 0 && form.skipped > 0},
						{/if}
						{#if form.skipped > 0}Skipped {form.skipped} existing {label.plural.toLowerCase()}{/if}
					</div>
				</div>

				{#if form.items && form.items.length > 0}
					<div class="mb-4">
						<h5 class="font-semibold text-sm mb-2 text-green-600">Created {label.plural}:</h5>
						<div class="space-y-1">
							{#each form.items as item}
								<div class="text-sm">
									<a href="{routePath}/{item.id}" class="text-indigo-600 hover:text-indigo-400">
										{item.name}
									</a>
									{#if item.ref_id}
										<span class="text-surface-600-400 text-xs">({item.ref_id})</span>
									{/if}
									{#if item.type}
										<span class="text-surface-600-400">({item.type})</span>
									{/if}
									{#if item.parent}
										<span class="text-surface-400-600 text-xs">→ child of {item.parent}</span>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}

				{#if form.skipped_items && form.skipped_items.length > 0}
					<div class="mb-4">
						<h5 class="font-semibold text-sm mb-2 text-blue-600">
							Skipped Existing {label.plural}:
						</h5>
						<div class="space-y-1">
							{#each form.skipped_items as item}
								<div class="text-sm">
									<a href="{routePath}/{item.id}" class="text-indigo-600 hover:text-indigo-400">
										{item.name}
									</a>
									{#if item.ref_id}
										<span class="text-surface-600-400 text-xs">({item.ref_id})</span>
									{/if}
									{#if item.type}
										<span class="text-surface-600-400">({item.type})</span>
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
							<div class="text-sm p-2 bg-surface-50-950 rounded">
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
			<p class="text-sm text-surface-600-400">Results will appear here after submission</p>
		{/if}
	</div>
</div>
