<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext, tick } from 'svelte';

	interface Props {
		id: string;
		data: {
			label: string;
			refId?: string;
			type: 'PR' | 'SP' | string;
			externalLinkCount: number;
		};
	}

	let { id, data }: Props = $props();

	const board = getContext<{
		showExternalLinks: (id: string) => void;
		renameAsset: (id: string, name: string) => Promise<boolean>;
		toggleAssetType: (id: string) => Promise<boolean>;
		confirmDeleteAsset: (id: string, name: string) => void;
	}>('assetBoard');

	// `data.type` is always the raw code 'PR' or 'SP' (set by AssetBoard from `is_primary`).
	const isPrimary = $derived(data.type === 'PR');

	const accentClass = $derived(isPrimary ? 'bg-primary-400' : 'bg-tertiary-400');
	const borderClass = $derived(isPrimary ? 'border-primary-300' : 'border-tertiary-300');
	const pillClass = $derived(
		isPrimary
			? 'bg-primary-100 text-primary-700 border-primary-200'
			: 'bg-tertiary-100 text-tertiary-700 border-tertiary-200'
	);

	let hovered = $state(false);
	let editing = $state(false);
	let draftName = $state('');
	let saving = $state(false);
	let togglingType = $state(false);
	let inputEl = $state<HTMLInputElement | null>(null);

	async function handleToggleType(event: MouseEvent) {
		event.stopPropagation();
		event.preventDefault();
		if (togglingType) return;
		togglingType = true;
		try {
			await board?.toggleAssetType(id);
		} finally {
			// Guarantee the spinner clears even if the underlying call throws — without
			// this the pill would stay stuck on the spinner with no way to recover.
			togglingType = false;
		}
	}

	async function startEdit(event: MouseEvent) {
		event.stopPropagation();
		draftName = data.label;
		editing = true;
		await tick();
		inputEl?.focus();
		inputEl?.select();
	}

	async function commitEdit() {
		const trimmed = draftName.trim();
		if (!trimmed || trimmed === data.label) {
			editing = false;
			return;
		}
		saving = true;
		let ok = false;
		try {
			ok = (await board?.renameAsset(id, trimmed)) ?? false;
		} finally {
			// Guarantee the input becomes editable again even if renameAsset throws.
			saving = false;
		}
		if (ok) {
			editing = false;
		}
		// On failure: keep the input open so the user can retry; toast already shown
	}

	function cancelEdit() {
		editing = false;
		draftName = '';
	}

	function onInputKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			commitEdit();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			cancelEdit();
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="asset-node relative rounded-base border-[1.5px] bg-white px-3 py-2 min-w-[160px] max-w-[220px] select-none shadow-sm {borderClass}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base {accentClass}"></div>

	<div class="flex items-start gap-2 ml-1">
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-1.5">
				<button
					type="button"
					title="Click to switch between Primary (PR) and Support (SP)"
					disabled={togglingType}
					onclick={handleToggleType}
					onmousedown={(e) => e.stopPropagation()}
					ondblclick={(e) => e.stopPropagation()}
					class="nodrag nopan inline-block text-[9px] font-semibold uppercase tracking-wide rounded px-1 py-0.5 border cursor-pointer hover:brightness-90 active:scale-95 transition disabled:opacity-50 {pillClass}"
				>
					{#if togglingType}
						<i class="fa-solid fa-spinner fa-spin"></i>
					{:else}
						{isPrimary ? 'PR' : 'SP'}
					{/if}
				</button>
				{#if data.refId}
					<span class="text-[9px] text-surface-500 font-mono truncate">{data.refId}</span>
				{/if}
			</div>
			{#if editing}
				<input
					bind:this={inputEl}
					bind:value={draftName}
					onkeydown={onInputKeydown}
					onblur={commitEdit}
					onclick={(e) => e.stopPropagation()}
					ondblclick={(e) => e.stopPropagation()}
					onmousedown={(e) => e.stopPropagation()}
					disabled={saving}
					class="nodrag nopan mt-1 w-full text-[12px] font-semibold leading-tight text-surface-900 bg-white border border-primary-400 rounded px-1 py-0.5 outline-none"
				/>
			{:else}
				<div
					role="button"
					tabindex="0"
					title="Double-click to rename"
					class="text-[12px] font-semibold leading-tight text-surface-900 mt-1 break-words cursor-text"
					ondblclick={startEdit}
				>
					{data.label}
				</div>
			{/if}
		</div>
	</div>

	{#if data.externalLinkCount > 0}
		<button
			type="button"
			class="nopan nodrag absolute -top-2 -right-2 px-1.5 h-4 rounded-full bg-warning-400 text-white text-[9px] font-semibold flex items-center justify-center hover:bg-warning-500 cursor-pointer shadow"
			title="External links to assets in other domains"
			onclick={() => board?.showExternalLinks(id)}
		>
			+{data.externalLinkCount}
		</button>
	{/if}

	{#if hovered}
		<div class="nopan nodrag absolute -top-2 -left-2 flex gap-0.5">
			<a
				href="/assets/{id}/edit"
				target="_blank"
				rel="noopener"
				aria-label="Edit asset in new tab"
				title="Edit in new tab"
				class="w-4 h-4 rounded-full bg-surface-200 hover:bg-surface-300 text-surface-700 text-[8px] flex items-center justify-center cursor-pointer shadow"
				onclick={(e) => e.stopPropagation()}
				onmousedown={(e) => e.stopPropagation()}
			>
				<i class="fa-solid fa-pen text-[8px]"></i>
			</a>
			<button
				type="button"
				aria-label="Delete asset"
				title="Delete asset"
				class="w-4 h-4 rounded-full bg-error-500 hover:bg-error-600 text-white text-[8px] flex items-center justify-center cursor-pointer shadow"
				onclick={(e) => {
					e.stopPropagation();
					board?.confirmDeleteAsset(id, data.label);
				}}
				onmousedown={(e) => e.stopPropagation()}
			>
				<i class="fa-solid fa-trash text-[8px]"></i>
			</button>
		</div>
	{/if}

	<Handle
		type="target"
		position={Position.Top}
		class="!w-3 !h-3 !bg-surface-50 !border-2 !border-surface-600"
	/>
	<Handle
		type="source"
		position={Position.Bottom}
		class="!w-3 !h-3 !bg-surface-50 !border-2 !border-surface-600"
	/>
</div>
