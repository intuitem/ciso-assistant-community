<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

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

	let hovered = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="relative flex h-10 w-16 items-center justify-center rounded-full border-[1.5px] border-secondary-400 bg-secondary-500/15 text-[11px] font-bold text-secondary-700-300 select-none"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	{#if editor?.readonly}
		{data.operator}
	{:else}
		<button
			type="button"
			class="nopan nodrag h-full w-full rounded-full hover:bg-secondary-500/25"
			title="AND / OR"
			onclick={() => editor?.toggleOperator(id)}
		>
			{data.operator}
		</button>
	{/if}

	{#if hovered && !editor?.readonly}
		<button
			type="button"
			aria-label="Remove operator"
			class="nopan nodrag absolute -top-2 -left-2 flex h-4 w-4 items-center justify-center rounded-full bg-error-500 text-[8px] text-white hover:bg-error-600"
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
