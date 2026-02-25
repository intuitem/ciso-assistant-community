<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	interface Props {
		id: string;
		data: {
			label: string;
			iconClass?: string;
			stage: number;
			onDelete?: (id: string) => void;
			onToggleOperator?: (id: string) => void;
			logicOperator?: 'AND' | 'OR';
		};
	}

	let { id, data }: Props = $props();

	const STAGE_BORDER: Record<number, string> = {
		0: '#ec4899',
		1: '#8b5cf6',
		2: '#f97316',
		3: '#ef4444'
	};

	const STAGE_BG: Record<number, string> = {
		0: '#fdf2f8',
		1: '#f5f3ff',
		2: '#fff7ed',
		3: '#fef2f2'
	};

	let hovered = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="action-node relative rounded-md border-[1.5px] px-3 py-2 min-w-[140px] max-w-[180px] text-center select-none"
	style="background: {STAGE_BG[data.stage] ?? '#fff'}; border-color: {STAGE_BORDER[data.stage] ??
		'#8b5cf6'};"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	<!-- Stage accent bar -->
	<div
		class="absolute left-0 top-0 bottom-0 w-1 rounded-l-md"
		style="background: {STAGE_BORDER[data.stage] ?? '#8b5cf6'}"
	></div>

	<!-- Content -->
	<div class="flex items-center gap-2">
		{#if data.iconClass}
			<i class="{data.iconClass} text-[11px] text-gray-500"></i>
		{/if}
		<span class="text-[11px] leading-tight text-slate-800 truncate">{data.label}</span>
	</div>

	<!-- Logic operator badge (AND/OR) — shown when node has 2+ incoming edges -->
	{#if data.logicOperator}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<span
			class="absolute -left-8 top-1/2 -translate-y-1/2 px-1 py-0.5 rounded text-[9px] font-bold border cursor-pointer select-none hover:brightness-90"
			style="background: #ede9fe; border-color: #8b5cf6; color: #6d28d9; z-index: 10;"
			role="button"
			tabindex="-1"
			onmousedown={(e) => {
				e.stopPropagation();
				data.onToggleOperator?.(id);
			}}
		>
			{data.logicOperator}
		</span>
	{/if}

	<!-- Delete button on hover -->
	{#if hovered && data.onDelete}
		<button
			class="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-red-500 text-white text-[8px] flex items-center justify-center hover:bg-red-600 cursor-pointer"
			onmousedown={(e) => { e.stopPropagation(); data.onDelete?.(id); }}
		>
			✕
		</button>
	{/if}

	<!-- Input handle (left) — hidden for KNOW stage (0) -->
	{#if data.stage > 0}
		<Handle
			type="target"
			position={Position.Left}
			class="!w-3 !h-3 !bg-white !border-2 !border-violet-800"
		/>
	{/if}

	<!-- Output handle (right) -->
	<Handle
		type="source"
		position={Position.Right}
		class="!w-3 !h-3 !bg-white !border-2 !border-violet-800"
	/>
</div>
