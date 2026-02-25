<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	interface Props {
		id: string;
		data: {
			operator: 'AND' | 'OR';
			onToggle?: (id: string) => void;
		};
	}

	let { id, data }: Props = $props();

	let hovered = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="logic-gate-node flex items-center justify-center w-10 h-10 rounded-full border-[1.5px] border-violet-800 cursor-pointer select-none"
	style="background: {hovered ? '#f3e8ff' : '#ffffff'}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	onclick={() => data.onToggle?.(id)}
>
	<span class="text-[11px] font-bold text-violet-800">{data.operator}</span>

	<Handle
		type="target"
		position={Position.Left}
		class="!w-2 !h-2 !bg-white !border-[1.5px] !border-violet-800"
	/>
	<Handle
		type="source"
		position={Position.Right}
		class="!w-2 !h-2 !bg-white !border-[1.5px] !border-violet-800"
	/>
</div>
