<script lang="ts">
	import { BaseEdge, EdgeLabel, getSmoothStepPath, type EdgeProps } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import { m } from '$paraglide/messages';

	let {
		sourceX,
		sourceY,
		targetX,
		targetY,
		sourcePosition,
		targetPosition,
		data,
		markerEnd,
		style
	}: EdgeProps = $props();

	const editor = getContext<{
		toggleOperator: (id: string) => void;
		readonly: boolean;
	}>('killChainEditor');

	const STAGE_CLASSES: Record<number, { bg: string; border: string; text: string }> = {
		0: { bg: 'bg-pink-50', border: 'border-pink-400', text: 'text-pink-700' },
		1: { bg: 'bg-violet-50', border: 'border-violet-400', text: 'text-violet-700' },
		2: { bg: 'bg-orange-50', border: 'border-orange-400', text: 'text-orange-700' },
		3: { bg: 'bg-red-50', border: 'border-red-400', text: 'text-red-700' }
	};

	const [path] = $derived(
		getSmoothStepPath({
			sourceX,
			sourceY,
			targetX,
			targetY,
			sourcePosition,
			targetPosition
		})
	);

	const convergenceX = $derived(targetX - 35);
	const convergenceY = $derived(targetY);

	const logicOp = $derived(data?.logicOp as 'AND' | 'OR' | null);
	const logicOpLabel = $derived(
		logicOp === 'AND' ? m.logicAnd() : logicOp === 'OR' ? m.logicOr() : null
	);
	const targetStage = $derived((data?.targetStage as number) ?? 1);
	const cls = $derived(STAGE_CLASSES[targetStage] ?? STAGE_CLASSES[1]);
</script>

<BaseEdge {path} {markerEnd} />
{#if logicOp}
	<EdgeLabel
		x={convergenceX}
		y={convergenceY}
		class="!bg-transparent !border-0 !shadow-none !p-0 !min-w-0 !min-h-0"
	>
		{#if editor?.readonly}
			<span
				class="px-1.5 py-0.5 rounded-full text-[9px] font-bold border {cls.bg} {cls.border} {cls.text}"
			>
				{logicOpLabel}
			</span>
		{:else}
			<button
				type="button"
				aria-label="Toggle logic operator"
				class="nopan nodrag px-1.5 py-0.5 rounded-full text-[9px] font-bold border cursor-pointer select-none hover:brightness-90 transition-colors {cls.bg} {cls.border} {cls.text}"
				onclick={(e) => {
					e.stopPropagation();
					if (data?.targetNodeId) editor?.toggleOperator(data.targetNodeId as string);
				}}
			>
				{logicOpLabel}
			</button>
		{/if}
	</EdgeLabel>
{/if}
