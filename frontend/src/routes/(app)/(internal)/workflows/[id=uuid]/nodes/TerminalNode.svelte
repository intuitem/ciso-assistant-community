<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import { m } from '$paraglide/messages';

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

	const editor = getContext<{ readonly: boolean; deleteNode: (id: string) => void }>(
		'workflowEditor'
	);

	let hovered = $state(false);

	const handleClass = $derived(
		editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600-400'
	);
</script>

<!-- Deliberately alarming (spec D35): this node stops the WHOLE run, cancelling
	every branch still in flight. The danger has to read off the canvas, because
	the safe way to finish one branch is simply to leave its last step unwired. -->
<div class="terminal-node flex flex-col items-center gap-1 select-none">
	<div
		class="relative flex items-center justify-center w-14 h-14 rounded-full border-2 transition-shadow
		bg-error-100-900 border-error-500 text-error-700-300
		{selected ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-surface-50-950' : ''}
		{data.error ? 'ring-2 ring-error-500' : ''}
		{data.runState === 'visited' ? 'ring-2 ring-success-400' : ''}
		{data.runState === 'active' ? 'ring-2 ring-warning-400 animate-pulse' : ''}"
		title={data.error ?? m.workflowNodeEndHint()}
		data-testid="workflow-node-{data.nodeType}"
		onmouseenter={() => (hovered = true)}
		onmouseleave={() => (hovered = false)}
	>
		<i class="fa-solid fa-circle-stop text-lg"></i>
		<Handle type="target" position={Position.Left} class={handleClass} />

		{#if hovered && !editor?.readonly && !data.error}
			<!-- Overlaps the circle's fill (round node: a -top-2/-right-2 corner
			     button would sit in the fill's dead corner, so the pointer leaves
			     the hovered circle before reaching it). Slightly larger + inset so
			     hover region and button stay contiguous. -->
			<button
				type="button"
				aria-label="Delete node"
				class="nopan nodrag absolute -top-1 -right-1 w-5 h-5 rounded-full bg-error-500 text-white text-[10px] flex items-center justify-center hover:bg-error-600 cursor-pointer"
				onclick={(e) => {
					e.stopPropagation();
					editor?.deleteNode(id);
				}}
			>
				✕
			</button>
		{/if}

		{#if data.error}
			<span
				class="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-error-500 text-white text-[9px] flex items-center justify-center"
			>
				!
			</span>
		{/if}
	</div>

	<span class="text-[10px] font-medium leading-tight text-error-700-300 whitespace-nowrap">
		{m.workflowNodeEnd()}
	</span>
</div>
