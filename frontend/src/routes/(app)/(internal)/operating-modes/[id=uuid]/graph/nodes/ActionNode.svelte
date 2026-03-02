<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		data: {
			label: string;
			iconClass?: string;
			stage: number;
			logicOp?: 'AND' | 'OR' | null;
		};
	}

	let { id, data }: Props = $props();

	const editor = getContext<{
		deleteNode: (id: string) => void;
		toggleOperator: (id: string) => void;
		readonly: boolean;
	}>('killChainEditor');

	const STAGE_CLASSES: Record<number, { border: string; accent: string }> = {
		0: { border: 'border-pink-300', accent: 'bg-pink-400' },
		1: { border: 'border-violet-300', accent: 'bg-violet-400' },
		2: { border: 'border-orange-300', accent: 'bg-orange-400' },
		3: { border: 'border-red-300', accent: 'bg-red-400' }
	};

	const stageClass = $derived(STAGE_CLASSES[data.stage] ?? STAGE_CLASSES[1]);

	let hovered = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="action-node relative rounded-base border-[1.5px] px-3 py-2 min-w-[140px] max-w-[180px] text-center select-none bg-surface-50 {stageClass.border}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	<!-- Stage accent bar -->
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base {stageClass.accent}"></div>

	<!-- Content -->
	<div class="flex items-center gap-2">
		{#if data.iconClass}
			<i class="{data.iconClass} text-[11px] text-surface-500"></i>
		{/if}
		<span class="text-[11px] leading-tight text-surface-900 truncate">{data.label}</span>
	</div>

	<!-- Delete button on hover (edit mode only) -->
	{#if hovered && !editor?.readonly}
		<button
			class="nopan nodrag absolute -top-2 -right-2 w-4 h-4 rounded-full bg-error-500 text-white text-[8px] flex items-center justify-center hover:bg-error-600 cursor-pointer"
			onclick={() => editor?.deleteNode(id)}
		>
			✕
		</button>
	{/if}

	<!-- Handles -->
	<Handle
		type="target"
		position={Position.Left}
		class={editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50 !border-2 !border-surface-600'}
	/>
	<Handle
		type="source"
		position={Position.Right}
		class={editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50 !border-2 !border-surface-600'}
	/>
</div>
