<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		selected?: boolean;
		data: {
			nodeType: 'end';
			error?: string | null;
			runState?: 'visited' | 'active' | 'error' | null;
		};
	}

	let { id, selected = false, data }: Props = $props();

	const editor = getContext<{ readonly: boolean }>('workflowEditor');

	const handleClass = $derived(
		editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600-400'
	);
</script>

<div
	class="terminal-node relative flex items-center justify-center w-14 h-14 rounded-full border-2 select-none transition-shadow
	bg-surface-200-800 border-surface-600-400 text-surface-800-200
	{selected ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-surface-50-950' : ''}
	{data.error ? 'ring-2 ring-error-500' : ''}
	{data.runState === 'visited' ? 'ring-2 ring-success-400' : ''}
	{data.runState === 'active' ? 'ring-2 ring-warning-400 animate-pulse' : ''}"
	title={data.error ?? undefined}
	data-testid="workflow-node-{data.nodeType}"
>
	<i class="fa-solid fa-flag-checkered text-sm"></i>

	{#if data.error}
		<span
			class="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-error-500 text-white text-[9px] flex items-center justify-center"
		>
			!
		</span>
	{/if}

	<Handle type="target" position={Position.Left} class={handleClass} />
</div>
