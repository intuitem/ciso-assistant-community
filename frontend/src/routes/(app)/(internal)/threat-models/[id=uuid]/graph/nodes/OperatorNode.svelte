<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		id: string;
		data: { operator: 'AND' | 'OR' };
	}

	let { id, data }: Props = $props();

	const editor = getContext<{
		deleteNode: (id: string) => void;
		toggleOperator: (id: string) => void;
		readonly: boolean;
	}>('threatModelEditor');
</script>

<div
	class="group relative flex h-10 w-16 items-center justify-center rounded-full border-[1.5px] border-secondary-400 bg-secondary-500/15 text-[11px] font-bold text-secondary-700-300 select-none"
>
	{#if editor?.readonly}
		{data.operator}
	{:else}
		<button
			type="button"
			class="h-full w-full cursor-grab rounded-full hover:bg-secondary-500/25 active:cursor-grabbing"
			title={m.toggleLogicOperator()}
			aria-label={m.toggleLogicOperator()}
			onclick={() => editor?.toggleOperator(id)}
		>
			{data.operator}
		</button>
	{/if}

	{#if !editor?.readonly}
		<button
			type="button"
			aria-label={m.removeNode()}
			class="nopan nodrag absolute -top-2 -left-2 flex h-4 w-4 items-center justify-center rounded-full bg-error-500 text-[8px] text-white opacity-0 transition-opacity hover:bg-error-600 focus:opacity-100 group-hover:opacity-100"
			onclick={() => editor?.deleteNode(id)}
		>
			✕
		</button>
	{/if}

	<Handle
		type="target"
		position={Position.Left}
		class="!w-3 !h-3 !bg-surface-50-950 !border-2 !border-secondary-500"
	/>
	<Handle
		type="source"
		position={Position.Right}
		class="!w-3 !h-3 !bg-surface-50-950 !border-2 !border-secondary-500"
	/>
</div>
