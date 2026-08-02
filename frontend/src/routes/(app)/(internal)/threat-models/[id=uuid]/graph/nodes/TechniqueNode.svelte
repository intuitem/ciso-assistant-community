<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		id: string;
		data: {
			label: string;
			refId?: string | null;
			parentName?: string | null;
			isHighlighted?: boolean;
		};
	}

	let { id, data }: Props = $props();

	const editor = getContext<{
		deleteNode: (id: string) => void;
		readonly: boolean;
	}>('threatModelEditor');
</script>

<div
	class="group relative rounded-base border-[1.5px] bg-surface-50-950 px-3 py-2 min-w-[150px] max-w-[190px] select-none {data.isHighlighted
		? 'border-warning-500'
		: 'border-surface-300-700'}"
>
	<div
		class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base {data.isHighlighted
			? 'bg-warning-500'
			: 'bg-primary-400'}"
	></div>

	{#if data.refId}
		<p class="text-[10px] font-mono text-surface-600-400 leading-none">{data.refId}</p>
	{/if}
	{#if data.parentName}
		<p class="text-[10px] text-surface-600-400 leading-tight text-wrap mt-1">{data.parentName}:</p>
	{/if}
	<p class="text-[11px] font-semibold leading-tight text-surface-900-100 text-wrap mt-0.5">
		{data.label}
	</p>

	{#if !editor?.readonly}
		<button
			type="button"
			aria-label={m.removeNode()}
			class="nopan nodrag absolute -top-2 -left-2 w-4 h-4 rounded-full bg-error-500 text-white text-[8px] flex items-center justify-center hover:bg-error-600 cursor-pointer opacity-0 transition-opacity focus:opacity-100 group-hover:opacity-100"
			onclick={() => editor?.deleteNode(id)}
		>
			✕
		</button>
	{/if}

	<Handle
		type="target"
		position={Position.Left}
		class={editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600-400'}
	/>
	<Handle
		type="source"
		position={Position.Right}
		class={editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600-400'}
	/>
</div>
