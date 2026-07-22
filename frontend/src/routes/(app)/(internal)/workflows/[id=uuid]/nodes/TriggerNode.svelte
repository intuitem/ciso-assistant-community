<script lang="ts" module>
	export const TRIGGER_ICONS: Record<string, string> = {
		manual: 'fa-hand-pointer',
		webhook: 'fa-satellite-dish',
		schedule: 'fa-clock',
		internal_event: 'fa-rss'
	};
</script>

<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		selected?: boolean;
		data: {
			nodeType: 'trigger';
			label: string;
			meta?: string | null;
			triggerType?: string;
			registration?: { enabled: boolean } | null;
			error?: string | null;
			runState?: 'visited' | 'active' | 'error' | null;
		};
	}

	let { id, selected = false, data }: Props = $props();

	const editor = getContext<{
		readonly: boolean;
		deleteNode: (id: string) => void;
	}>('workflowEditor');

	const icon = $derived(TRIGGER_ICONS[data.triggerType ?? 'manual'] ?? 'fa-bolt');
	let hovered = $state(false);
	const handleClass = $derived(
		editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600-400'
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="trigger-node relative rounded-base border-[1.5px] bg-surface-50-950 px-3 py-2 min-w-[160px] max-w-[220px] select-none transition-shadow
	border-success-300 dark:border-success-700
	{selected
		? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-surface-50-950 shadow-lg'
		: 'shadow-sm'}
	{data.error ? 'ring-2 ring-error-500' : ''}
	{data.runState === 'visited' ? 'ring-2 ring-success-400' : ''}
	{data.runState === 'active' ? 'ring-2 ring-warning-400 animate-pulse' : ''}
	{data.runState === 'error' ? 'ring-2 ring-error-500 animate-pulse' : ''}"
	title={data.error ?? undefined}
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	data-testid="workflow-node-trigger-{data.triggerType ?? 'manual'}"
>
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base bg-success-500"></div>

	<div class="flex items-center gap-2 pl-1">
		<i class="fa-solid {icon} text-xs text-surface-700-300"></i>
		<span class="text-xs font-semibold leading-tight text-surface-900-100 text-wrap">
			{data.label}
		</span>
		{#if data.registration}
			<span
				class="ml-auto w-2 h-2 rounded-full shrink-0 {data.registration.enabled
					? 'bg-success-500 animate-pulse'
					: 'bg-surface-400-600'}"
				data-testid="trigger-armed-dot"
			></span>
		{/if}
	</div>

	{#if data.meta}
		<p class="pl-1 mt-1 text-[10px] text-surface-600-400 truncate">{data.meta}</p>
	{/if}

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

	<Handle type="source" position={Position.Right} class={handleClass} />
</div>
