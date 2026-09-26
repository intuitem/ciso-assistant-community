<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		data: {
			label: string;
			refId?: string;
			type: 'PR' | 'SP' | string;
			folderId?: string;
			folderName?: string;
			hidden?: boolean;
			pinned?: boolean;
			linked?: boolean;
		};
	}

	let { id, data }: Props = $props();

	const board = getContext<{
		unpinGhost: (id: string) => void;
	}>('assetBoard');

	let hovered = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="relative rounded-base border-[1.5px] border-dashed px-3 py-2 min-w-[160px] max-w-[220px] select-none opacity-80 hover:opacity-100 transition-opacity
		{data.hidden ? 'border-surface-400 bg-surface-100-900' : 'border-warning-400 bg-warning-50-950'}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	{#if data.hidden}
		<div class="flex items-center gap-2 text-surface-500">
			<i class="fa-solid fa-lock text-[11px]"></i>
			<div class="text-[12px] font-semibold leading-tight">Hidden asset</div>
		</div>
		<div class="text-[10px] text-surface-500 mt-1">In a domain you cannot view</div>
	{:else}
		<div class="flex items-center gap-1.5 min-w-0">
			<span
				class="inline-flex items-center gap-1 text-[9px] font-semibold rounded px-1 py-0.5 border border-warning-300 bg-warning-100 text-warning-800 truncate max-w-[160px]"
				title={data.folderName}
			>
				<i class="fa-solid fa-sitemap text-[8px]"></i>{data.folderName}
			</span>
			<span class="text-[9px] font-semibold uppercase text-surface-500">{data.type}</span>
		</div>
		{#if data.refId}
			<div class="text-[9px] text-surface-500 font-mono truncate mt-1">{data.refId}</div>
		{/if}
		<div class="text-[12px] font-semibold leading-tight text-surface-800-200 mt-1 break-words">
			{data.label}
		</div>
	{/if}

	{#if hovered && !data.hidden}
		<div class="nopan nodrag absolute -top-2 -left-2 flex gap-0.5">
			<a
				href="?folder={data.folderId}"
				data-sveltekit-reload
				aria-label="Open its domain board"
				title="Open {data.folderName} board"
				class="w-4 h-4 rounded-full bg-warning-400 hover:bg-warning-500 text-white flex items-center justify-center cursor-pointer shadow"
				onmousedown={(e) => e.stopPropagation()}
			>
				<i class="fa-solid fa-arrow-right text-[8px]"></i>
			</a>
			{#if data.pinned && !data.linked}
				<button
					type="button"
					aria-label="Remove from board"
					title="Remove from board"
					class="w-4 h-4 rounded-full bg-surface-300 hover:bg-surface-400 text-surface-800 flex items-center justify-center cursor-pointer shadow"
					onclick={(e) => {
						e.stopPropagation();
						board?.unpinGhost(id);
					}}
					onmousedown={(e) => e.stopPropagation()}
				>
					<i class="fa-solid fa-xmark text-[8px]"></i>
				</button>
			{/if}
		</div>
	{/if}

	<Handle
		type="target"
		position={Position.Top}
		isConnectable={!data.hidden}
		class="!w-3 !h-3 !bg-surface-50-950 !border-2 !border-dashed !border-warning-500"
	/>
	<Handle
		type="source"
		position={Position.Bottom}
		isConnectable={!data.hidden}
		class="!w-3 !h-3 !bg-surface-50-950 !border-2 !border-dashed !border-warning-500"
	/>
</div>
