<script lang="ts">
	import { NodeResizer } from '@xyflow/svelte';
	import { getContext, tick } from 'svelte';

	interface Props {
		id: string;
		selected?: boolean;
		data: {
			label: string;
			color: string;
		};
	}

	let { id, data, selected = false }: Props = $props();

	const board = getContext<{
		renameZone: (id: string, name: string) => void;
		recolorZone: (id: string, color: string) => void;
		deleteZone: (id: string) => void;
		resizeZone: (id: string, width: number, height: number) => void;
	}>('assetBoard');

	const PALETTE = [
		'#3b82f6', // blue
		'#10b981', // green
		'#f59e0b', // amber
		'#ef4444', // red
		'#8b5cf6', // violet
		'#64748b' // slate
	];

	let editing = $state(false);
	let draftName = $state('');
	let inputEl = $state<HTMLInputElement | null>(null);
	let paletteOpen = $state(false);
	let hovered = $state(false);

	// hex -> rgba(.., alpha) for translucent fill, without pulling a colour lib
	function tint(hex: string, alpha: number): string {
		const h = hex.replace('#', '');
		const r = parseInt(h.slice(0, 2), 16);
		const g = parseInt(h.slice(2, 4), 16);
		const b = parseInt(h.slice(4, 6), 16);
		return `rgba(${r}, ${g}, ${b}, ${alpha})`;
	}

	async function startEdit(event: MouseEvent) {
		event.stopPropagation();
		draftName = data.label;
		editing = true;
		await tick();
		inputEl?.focus();
		inputEl?.select();
	}

	function commitEdit() {
		const trimmed = draftName.trim();
		if (trimmed && trimmed !== data.label) {
			board.renameZone(id, trimmed);
		}
		editing = false;
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

<div
	class="trust-zone relative w-full h-full rounded-lg"
	style:background-color={tint(data.color, 0.08)}
	style:border="2px dashed {data.color}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	role="group"
>
	<NodeResizer
		minWidth={140}
		minHeight={100}
		color={data.color}
		isVisible={selected || hovered}
		onResizeEnd={(_e, params) => board.resizeZone(id, params.width, params.height)}
	/>

	<!-- Header bar: label + actions. nopan/nodrag so clicks here don't move the zone. -->
	<div
		class="absolute top-0 left-0 right-0 flex items-center justify-between gap-1 px-2 py-1 rounded-t-lg border-b text-[11px] font-semibold"
		style:background-color={tint(data.color, 0.18)}
		style:color={data.color}
		style:border-color={tint(data.color, 0.3)}
	>
		{#if editing}
			<!-- svelte-ignore a11y_autofocus -->
			<input
				bind:this={inputEl}
				bind:value={draftName}
				onkeydown={onInputKeydown}
				onblur={commitEdit}
				onclick={(e) => e.stopPropagation()}
				onmousedown={(e) => e.stopPropagation()}
				class="nodrag nopan flex-1 min-w-0 px-1 py-0.5 text-[11px] font-semibold bg-white border border-surface-300 rounded outline-none text-surface-900"
			/>
		{:else}
			<button
				type="button"
				class="nodrag nopan flex-1 min-w-0 text-left truncate cursor-text bg-transparent"
				title="Double-click to rename"
				ondblclick={startEdit}
			>
				<i class="fa-solid fa-shield-halved mr-1 opacity-70"></i>{data.label}
			</button>
		{/if}

		<div class="nodrag nopan relative flex items-center gap-1 shrink-0">
			<button
				type="button"
				title="Change colour"
				class="w-4 h-4 rounded-full border border-white/40 cursor-pointer"
				style:background-color={data.color}
				onclick={(e) => {
					e.stopPropagation();
					paletteOpen = !paletteOpen;
				}}
				aria-label="Change colour"
			></button>
			{#if paletteOpen}
				<div
					class="absolute top-5 right-0 z-10 flex gap-1 p-1 bg-white rounded shadow border border-surface-300"
				>
					{#each PALETTE as c (c)}
						<button
							type="button"
							class="w-4 h-4 rounded-full border border-surface-300 cursor-pointer hover:scale-110 transition"
							style:background-color={c}
							onclick={(e) => {
								e.stopPropagation();
								board.recolorZone(id, c);
								paletteOpen = false;
							}}
							aria-label="Set colour {c}"
						></button>
					{/each}
				</div>
			{/if}
			<button
				type="button"
				class="w-4 h-4 rounded-full bg-error-500 hover:bg-error-600 text-white text-[9px] flex items-center justify-center cursor-pointer"
				title="Delete zone (assets stay on canvas)"
				onclick={(e) => {
					e.stopPropagation();
					board.deleteZone(id);
				}}
				aria-label="Delete zone"
			>
				<i class="fa-solid fa-trash text-[8px]"></i>
			</button>
		</div>
	</div>
</div>

<style>
	.trust-zone {
		box-sizing: border-box;
		padding-top: 22px;
	}
</style>
