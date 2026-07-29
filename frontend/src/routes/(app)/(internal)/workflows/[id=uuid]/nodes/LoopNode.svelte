<script lang="ts">
	import { m } from '$paraglide/messages';
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		selected?: boolean;
		data: {
			nodeType: 'loop';
			label: string;
			meta?: string | null;
			visitCount?: number | null;
			error?: string | null;
			runState?: 'visited' | 'active' | 'error' | 'warning' | null;
		};
	}

	let { id, selected = false, data }: Props = $props();

	const editor = getContext<{
		readonly: boolean;
		deleteNode: (id: string) => void;
	}>('workflowEditor');

	let hovered = $state(false);
	const portClass = $derived(
		editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-4 !h-4 !bg-surface-50-950 !border-2 !border-surface-600-400 hover:!border-primary-500'
	);
	const targetHandleClass = $derived(
		editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600-400'
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="loop-node relative rounded-base border-[1.5px] bg-surface-50-950 py-2 w-[190px] select-none transition-shadow
	border-secondary-300 dark:border-secondary-700
	{selected
		? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-surface-50-950 shadow-lg'
		: 'shadow-sm'}
	{data.error ? 'ring-2 ring-error-500' : ''}
	{data.runState === 'visited' ? 'ring-2 ring-success-400' : ''}
	{data.runState === 'active' ? 'ring-2 ring-warning-400 animate-pulse' : ''}
	{data.runState === 'error' ? 'ring-2 ring-error-500 animate-pulse' : ''}
	{data.runState === 'warning' ? 'ring-2 ring-warning-500' : ''}"
	title={data.error ?? undefined}
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	data-testid="workflow-node-loop"
>
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base bg-secondary-500"></div>

	<div class="flex items-center gap-2 pl-4 pr-3">
		<i class="fa-solid fa-rotate text-xs text-surface-700-300"></i>
		<span class="text-xs font-semibold leading-tight text-surface-900-100 text-wrap">
			{data.label}
		</span>
		{#if data.visitCount && data.visitCount > 1}
			<span class="ml-auto badge preset-tonal text-[9px] shrink-0">×{data.visitCount}</span>
		{/if}
	</div>

	{#if data.meta}
		<p class="pl-4 pr-3 mt-1 text-[10px] text-surface-600-400 truncate">{data.meta}</p>
	{/if}

	<div class="mt-1.5 space-y-0.5">
		<div class="nodrag relative flex items-center justify-end min-h-[22px] pl-4 pr-3 py-0.5">
			<span class="text-[10px] leading-tight text-surface-700-300">
				<i class="fa-solid fa-rotate mr-1 text-[8px]"></i>{m.loopPortEach()}
			</span>
			<Handle
				id="each"
				type="source"
				position={Position.Right}
				isConnectable={!editor?.readonly}
				class={portClass}
			/>
		</div>
		<div
			class="nodrag relative flex items-center justify-end min-h-[22px] pl-4 pr-3 py-0.5 mt-1 pt-1 border-t border-surface-200-800"
		>
			<span class="text-[10px] leading-tight text-surface-600-400">
				<i class="fa-solid fa-flag-checkered mr-1 text-[8px]"></i>{m.loopPortDone()}
			</span>
			<Handle
				id="done"
				type="source"
				position={Position.Right}
				isConnectable={!editor?.readonly}
				class={portClass}
			/>
		</div>
	</div>

	{#if data.error}
		<span
			class="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-error-500 text-white text-[9px] flex items-center justify-center"
		>
			!
		</span>
	{/if}

	{#if data.runState === 'visited'}
		<span
			class="absolute -top-2 -left-2 w-4 h-4 rounded-full bg-success-500 text-white text-[8px] flex items-center justify-center"
		>
			<i class="fa-solid fa-check"></i>
		</span>
	{:else if data.runState === 'active'}
		<span
			class="absolute -top-2 -left-2 w-4 h-4 rounded-full bg-warning-500 text-white text-[8px] flex items-center justify-center"
		>
			<i class="fa-solid fa-circle-notch fa-spin"></i>
		</span>
	{:else if data.runState === 'warning'}
		<span
			class="absolute -top-2 -left-2 w-4 h-4 rounded-full bg-warning-500 text-white text-[8px] flex items-center justify-center"
		>
			!
		</span>
	{/if}

	{#if hovered && !editor?.readonly && !data.error}
		<button
			type="button"
			aria-label="Delete node"
			class="nopan nodrag absolute -top-2 -right-2 w-4 h-4 rounded-full bg-error-500 text-white text-[8px] flex items-center justify-center hover:bg-error-600 cursor-pointer"
			onclick={(e) => {
				e.stopPropagation();
				editor?.deleteNode(id);
			}}
		>
			✕
		</button>
	{/if}

	<Handle type="target" position={Position.Left} class={targetHandleClass} />
</div>
