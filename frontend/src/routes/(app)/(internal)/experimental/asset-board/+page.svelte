<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { createPickerForm } from '$lib/components/AssetGraph/picker';
	import AssetBoard from './AssetBoard.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const folderPicker = createPickerForm('folder', data.selectedFolderId || null);

	function handleFolderChange(folderId: string | null) {
		const url = new URL(page.url);
		if (folderId) {
			url.searchParams.set('folder', folderId);
		} else {
			url.searchParams.delete('folder');
		}
		goto(url, { replaceState: false, invalidateAll: true });
	}
</script>

<div class="flex flex-col h-[calc(100vh-9rem)]">
	<div class="flex items-center gap-3 mb-3 bg-surface-50-950 shadow-sm rounded-base p-3">
		<h4 class="font-bold text-surface-800-200">
			<i class="fa-solid fa-diagram-project mr-2"></i>Asset whiteboard
		</h4>
		<span
			class="text-xs text-surface-500 px-2 py-0.5 rounded bg-surface-100-900 border border-surface-200-800"
		>
			experimental
		</span>
		<div class="flex-1"></div>
		<span class="text-sm font-medium text-surface-700-300">Domain:</span>
		<div class="w-80">
			<FolderTreeSelect
				form={folderPicker.form}
				field="folder"
				writePermission={null}
				nullable
				onChange={handleFolderChange}
			/>
		</div>
	</div>

	<div class="flex-1 min-h-0">
		{#if data.selectedFolderId}
			{#key data.selectedFolderId}
				<AssetBoard
					assets={data.assets}
					externalAssets={data.externalAssets}
					hiddenAssetIds={data.hiddenAssetIds}
					folderId={data.selectedFolderId}
					assetModel={data.assetModel}
					deleteForm={data.assetDeleteForm}
				/>
			{/key}
		{:else}
			<div
				class="h-full flex items-center justify-center bg-surface-50-950 rounded-base border border-dashed border-surface-300-700 text-surface-500"
			>
				<div class="text-center">
					<i class="fa-solid fa-diagram-project text-4xl mb-3 text-surface-300"></i>
					<p class="text-sm">Select a domain to start mapping its assets.</p>
				</div>
			</div>
		{/if}
	</div>
</div>
