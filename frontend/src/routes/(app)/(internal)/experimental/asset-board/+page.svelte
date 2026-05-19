<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import AssetBoard from './AssetBoard.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let selectedFolderId = $state(data.selectedFolderId ?? '');

	function handleFolderChange() {
		const url = new URL(page.url);
		if (selectedFolderId) {
			url.searchParams.set('folder', selectedFolderId);
		} else {
			url.searchParams.delete('folder');
		}
		goto(url, { replaceState: false, invalidateAll: true });
	}
</script>

<div class="flex flex-col h-[calc(100vh-9rem)]">
	<div class="flex items-center gap-3 mb-3 bg-white shadow-sm rounded-base p-3">
		<h4 class="font-bold text-surface-800">
			<i class="fa-solid fa-diagram-project mr-2"></i>Asset whiteboard
		</h4>
		<span
			class="text-xs text-surface-500 px-2 py-0.5 rounded bg-surface-100 border border-surface-200"
		>
			experimental
		</span>
		<div class="flex-1"></div>
		<label class="text-sm font-medium text-surface-700" for="board-folder">Domain:</label>
		<select
			id="board-folder"
			bind:value={selectedFolderId}
			onchange={handleFolderChange}
			class="rounded-lg border-gray-300 text-gray-700 sm:text-sm"
		>
			<option value="">Select a domain</option>
			{#each data.folders as folder}
				<option value={folder.id}>{folder.str || folder.name}</option>
			{/each}
		</select>
	</div>

	<div class="flex-1 min-h-0">
		{#if data.selectedFolderId}
			{#key data.selectedFolderId}
				<AssetBoard
					assets={data.assets}
					folderId={data.selectedFolderId}
					assetModel={data.assetModel}
					deleteForm={data.assetDeleteForm}
				/>
			{/key}
		{:else}
			<div
				class="h-full flex items-center justify-center bg-surface-50 rounded-base border border-dashed border-surface-300 text-surface-500"
			>
				<div class="text-center">
					<i class="fa-solid fa-diagram-project text-4xl mb-3 text-surface-300"></i>
					<p class="text-sm">Select a domain to start mapping its assets.</p>
				</div>
			</div>
		{/if}
	</div>
</div>
