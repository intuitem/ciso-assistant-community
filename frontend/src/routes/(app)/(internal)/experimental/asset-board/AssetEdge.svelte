<script lang="ts">
	import { BaseEdge, EdgeLabel, getBezierPath, type EdgeProps } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	let {
		sourceX,
		sourceY,
		targetX,
		targetY,
		sourcePosition,
		targetPosition,
		source,
		target,
		markerEnd,
		selected
	}: EdgeProps = $props();

	const board = getContext<{
		deleteEdge: (source: string, target: string) => void;
	}>('assetBoard');

	const [path, labelX, labelY] = $derived(
		getBezierPath({
			sourceX,
			sourceY,
			targetX,
			targetY,
			sourcePosition,
			targetPosition
		})
	);
</script>

<BaseEdge
	{path}
	{markerEnd}
	style={selected
		? 'stroke: var(--color-secondary-500); stroke-width: 3;'
		: 'stroke: var(--color-surface-500); stroke-width: 2;'}
/>

{#if selected}
	<EdgeLabel
		x={labelX}
		y={labelY}
		class="!bg-transparent !border-0 !shadow-none !p-0 !min-w-0 !min-h-0"
	>
		<button
			type="button"
			aria-label="Delete link"
			title="Delete link"
			class="nopan nodrag w-5 h-5 rounded-full bg-error-500 hover:bg-error-600 text-white text-[10px] flex items-center justify-center cursor-pointer shadow"
			onclick={(e) => {
				e.stopPropagation();
				board?.deleteEdge(source, target);
			}}
			onmousedown={(e) => e.stopPropagation()}
		>
			<i class="fa-solid fa-xmark text-[10px]"></i>
		</button>
	</EdgeLabel>
{/if}
