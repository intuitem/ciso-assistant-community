<script lang="ts">
	import { NodeResizer } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		data: { name: string; refId: string; count: number };
	}

	let { id, data }: Props = $props();

	const editor = getContext<{
		dragOverLane: string | null;
		dragTactics: string[] | null;
		readonly: boolean;
		markDirty: () => void;
	}>('threatModelEditor');

	const isHighlighted = $derived(editor?.dragOverLane === id);
	// while dragging, a lane the technique does not belong to is not a valid target
	const isRejecting = $derived(
		Boolean(editor?.dragTactics) && !editor.dragTactics!.includes(id.replace(/^lane-/, ''))
	);
</script>

{#if !editor?.readonly}
	<NodeResizer minWidth={220} minHeight={300} onResizeEnd={() => editor?.markDirty()} />
{/if}

<div
	class="w-full h-full rounded-xl overflow-hidden border-2 border-dashed transition-colors duration-200 cursor-grab active:cursor-grabbing {isHighlighted
		? 'border-primary-500 bg-primary-500/10'
		: isRejecting
			? 'border-surface-200-800 bg-surface-100-900/30 opacity-40'
			: 'border-surface-300-700 bg-surface-100-900/60'}"
>
	<div class="px-2 py-3 text-center">
		<p class="text-xs font-semibold text-surface-700-300 leading-tight">{data.name}</p>
		<p class="text-[10px] text-surface-500">{data.refId} · {data.count}</p>
	</div>
</div>
