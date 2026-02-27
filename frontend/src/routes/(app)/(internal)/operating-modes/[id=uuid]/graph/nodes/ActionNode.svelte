<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		data: {
			label: string;
			iconClass?: string;
			stage: number;
		};
	}

	let { id, data }: Props = $props();

	const editor = getContext<{
		logicOps: Map<string, 'AND' | 'OR'>;
		deleteNode: (id: string) => void;
		toggleOperator: (id: string) => void;
	}>('killChainEditor');

	const logicOperator = $derived(editor?.logicOps.get(id));

	const STAGE_CLASSES: Record<number, { bg: string; border: string; accent: string }> = {
		0: { bg: 'bg-pink-100', border: 'border-pink-400', accent: 'bg-pink-400' },
		1: { bg: 'bg-violet-100', border: 'border-violet-400', accent: 'bg-violet-400' },
		2: { bg: 'bg-orange-100', border: 'border-orange-400', accent: 'bg-orange-400' },
		3: { bg: 'bg-red-100', border: 'border-red-400', accent: 'bg-red-400' }
	};

	const stageClass = $derived(STAGE_CLASSES[data.stage] ?? STAGE_CLASSES[1]);

	let hovered = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="action-node relative rounded-base border-[1.5px] px-3 py-2 min-w-[140px] max-w-[180px] text-center select-none {stageClass.bg} {stageClass.border}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	<!-- Stage accent bar -->
	<div
		class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base {stageClass.accent}"
	></div>

	<!-- Content -->
	<div class="flex items-center gap-2">
		{#if data.iconClass}
			<i class="{data.iconClass} text-[11px] text-surface-500"></i>
		{/if}
		<span class="text-[11px] leading-tight text-surface-900 truncate">{data.label}</span>
	</div>

	<!-- Logic operator badge (AND/OR) — shown when node has 2+ incoming edges -->
	{#if logicOperator}
		<button
			class="nopan nodrag absolute -left-8 top-1/2 -translate-y-1/2 px-1 py-0.5 rounded-base text-[9px] font-bold border cursor-pointer select-none hover:brightness-90 bg-violet-100 border-violet-500 text-violet-700 z-10"
			onclick={() => editor?.toggleOperator(id)}
		>
			{logicOperator}
		</button>
	{/if}

	<!-- Delete button on hover -->
	{#if hovered}
		<button
			class="nopan nodrag absolute -top-2 -right-2 w-4 h-4 rounded-full bg-error-500 text-white text-[8px] flex items-center justify-center hover:bg-error-600 cursor-pointer"
			onclick={() => editor?.deleteNode(id)}
		>
			✕
		</button>
	{/if}

	<!-- Input handle (left) -->
	<Handle
		type="target"
		position={Position.Left}
		class="!w-3 !h-3 !bg-white !border-2 !border-primary-800"
	/>

	<!-- Output handle (right) -->
	<Handle
		type="source"
		position={Position.Right}
		class="!w-3 !h-3 !bg-white !border-2 !border-primary-800"
	/>
</div>
