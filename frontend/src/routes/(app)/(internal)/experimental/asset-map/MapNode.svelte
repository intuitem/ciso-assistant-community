<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		data: {
			label?: string;
			refId?: string;
			type?: string;
			folderId?: string;
			folderName?: string;
			folderPath?: string;
			hidden?: boolean;
			focus?: boolean;
			local?: boolean;
			omitted?: number;
			elsewhere?: number;
		};
	}

	let { id, data }: Props = $props();

	const map = getContext<{
		refocus: (id: string) => void;
		expand: (id: string) => void;
		reveal: (id: string) => void;
	}>('assetGraph');

	let hovered = $state(false);

	const isPrimary = $derived(data.type === 'PR');
	const tone = $derived(
		data.hidden
			? 'border-dashed border-surface-400 bg-surface-100-900 text-surface-500'
			: data.local
				? `bg-surface-50-950 ${isPrimary ? 'border-primary-300' : 'border-tertiary-300'}`
				: 'border-dashed border-warning-400 bg-warning-50-950'
	);
</script>

<div
	class="relative rounded-base border-[1.5px] px-3 py-2 min-w-[160px] max-w-[220px] select-none shadow-sm {tone}
		{data.focus ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-surface-50-950' : ''}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	ondblclick={() => !data.hidden && map?.refocus(id)}
	role="button"
	tabindex="-1"
>
	{#if data.hidden}
		<div class="flex items-center gap-2">
			<i class="fa-solid fa-lock text-[11px]"></i>
			<div class="text-[12px] font-semibold leading-tight">Hidden asset</div>
		</div>
		<div class="text-[10px] mt-1">In a domain you cannot view</div>
	{:else}
		<div class="flex items-center gap-1.5 min-w-0">
			<span
				class="inline-block text-[9px] font-semibold uppercase rounded px-1 py-0.5 border
					{isPrimary
					? 'bg-primary-100 text-primary-700 border-primary-200'
					: 'bg-tertiary-100 text-tertiary-700 border-tertiary-200'}"
			>
				{data.type}
			</span>
			<span
				class="inline-flex items-center gap-1 text-[9px] font-semibold rounded px-1 py-0.5 border truncate max-w-[150px]
					{data.local
					? 'border-surface-300 bg-surface-100 text-surface-700'
					: 'border-warning-300 bg-warning-100 text-warning-800'}"
				title={data.folderPath}
			>
				<i class="fa-solid fa-sitemap text-[8px]"></i>{data.folderName}
			</span>
		</div>
		{#if data.refId}
			<div class="text-[9px] text-surface-500 font-mono truncate mt-1">{data.refId}</div>
		{/if}
		<div class="text-[12px] font-semibold leading-tight text-surface-900-100 mt-1 break-words">
			{data.label}
		</div>
	{/if}

	{#if data.elsewhere}
		<button
			type="button"
			class="nopan nodrag absolute -bottom-2 -left-2 px-1.5 h-4 rounded-full text-[9px] font-semibold shadow border
				{data.hidden
				? 'bg-surface-200 text-surface-500 border-surface-300 cursor-default'
				: 'bg-surface-100 text-surface-700 border-surface-400 hover:bg-surface-200 cursor-pointer'}"
			title={data.hidden
				? 'Linked to other assets beyond a hidden asset'
				: 'Also linked to assets outside this chain'}
			disabled={data.hidden}
			onclick={(e) => {
				e.stopPropagation();
				map?.reveal(id);
			}}
			onmousedown={(e) => e.stopPropagation()}
		>
			<i class="fa-solid fa-arrow-up-right-from-square text-[7px] mr-0.5"></i>{data.elsewhere}
		</button>
	{/if}

	{#if data.omitted}
		<button
			type="button"
			class="nopan nodrag absolute -bottom-2 -right-2 px-1.5 h-4 rounded-full text-[9px] font-semibold shadow
				{data.hidden
				? 'bg-surface-300 text-surface-700 cursor-default'
				: 'bg-secondary-500 text-white hover:bg-secondary-600 cursor-pointer'}"
			title={data.hidden ? 'More links beyond a hidden asset' : 'Show the links not drawn yet'}
			disabled={data.hidden}
			onclick={(e) => {
				e.stopPropagation();
				map?.expand(id);
			}}
			onmousedown={(e) => e.stopPropagation()}
		>
			+{data.omitted}
		</button>
	{/if}

	{#if hovered && !data.hidden}
		<div class="nopan nodrag absolute -top-2 -left-2 flex gap-0.5">
			{#if !data.focus}
				<button
					type="button"
					aria-label="Focus on this asset"
					title="Focus on this asset"
					class="w-4 h-4 rounded-full bg-primary-500 hover:bg-primary-600 text-white flex items-center justify-center shadow cursor-pointer"
					onclick={(e) => {
						e.stopPropagation();
						map?.refocus(id);
					}}
					onmousedown={(e) => e.stopPropagation()}
					ondblclick={(e) => e.stopPropagation()}
				>
					<i class="fa-solid fa-crosshairs text-[8px]"></i>
				</button>
			{/if}
			<a
				href="/assets/{id}"
				target="_blank"
				rel="noopener"
				aria-label="Open asset"
				title="Open asset in a new tab"
				class="w-4 h-4 rounded-full bg-surface-200 hover:bg-surface-300 text-surface-700 flex items-center justify-center shadow"
				onmousedown={(e) => e.stopPropagation()}
			>
				<i class="fa-solid fa-up-right-from-square text-[8px]"></i>
			</a>
			<a
				href="/experimental/asset-board?folder={data.folderId}"
				aria-label="Open domain whiteboard"
				title="Open the {data.folderName} whiteboard"
				class="w-4 h-4 rounded-full bg-warning-400 hover:bg-warning-500 text-white flex items-center justify-center shadow"
				onmousedown={(e) => e.stopPropagation()}
			>
				<i class="fa-solid fa-diagram-project text-[8px]"></i>
			</a>
		</div>
	{/if}

	<Handle
		type="target"
		position={Position.Top}
		isConnectable={!data.hidden}
		class="!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600"
	/>
	<Handle
		type="source"
		position={Position.Bottom}
		isConnectable={!data.hidden}
		class="!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600"
	/>
</div>
