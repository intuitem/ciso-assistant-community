<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Props {
		id: string;
		selected?: boolean;
		data: {
			nodeType: 'task' | 'condition' | 'action' | 'subprocess' | 'event';
			label: string;
			meta?: string | null;
			assignments?: { role_code: string; is_blocking: boolean }[];
			error?: string | null;
			runState?: 'visited' | 'active' | 'error' | 'warning' | null;
		};
	}

	let { id, selected = false, data }: Props = $props();

	const editor = getContext<{
		readonly: boolean;
		deleteNode: (id: string) => void;
	}>('workflowEditor');

	const TYPE_STYLE: Record<string, { icon: string; accent: string; border: string; chip: string }> =
		{
			task: {
				icon: 'fa-clipboard-check',
				accent: 'bg-primary-500',
				border: 'border-primary-300 dark:border-primary-700',
				chip: 'preset-tonal-primary'
			},
			condition: {
				icon: 'fa-code-branch',
				accent: 'bg-warning-500',
				border: 'border-warning-300 dark:border-warning-700',
				chip: 'preset-tonal-warning'
			},
			action: {
				icon: 'fa-bolt',
				accent: 'bg-secondary-500',
				border: 'border-secondary-300 dark:border-secondary-700',
				chip: 'preset-tonal-secondary'
			},
			subprocess: {
				icon: 'fa-diagram-project',
				accent: 'bg-tertiary-500',
				border: 'border-tertiary-300 dark:border-tertiary-700',
				chip: 'preset-tonal-tertiary'
			},
			event: {
				icon: 'fa-tower-broadcast',
				accent: 'bg-surface-500',
				border: 'border-surface-300-700',
				chip: 'preset-tonal'
			}
		};

	const style = $derived(TYPE_STYLE[data.nodeType] ?? TYPE_STYLE.action);
	let hovered = $state(false);
	const handleClass = $derived(
		editor?.readonly
			? '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none'
			: '!w-3 !h-3 !bg-surface-50-950 !border-2 !border-surface-600-400'
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="step-node relative rounded-base border-[1.5px] bg-surface-50-950 px-3 py-2 min-w-[160px] max-w-[220px] select-none transition-shadow
	{style.border}
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
	data-testid="workflow-node-{data.nodeType}"
>
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base {style.accent}"></div>

	<div class="flex items-center gap-2 pl-1">
		<i class="fa-solid {style.icon} text-xs text-surface-700-300"></i>
		<span class="text-xs font-semibold leading-tight text-surface-900-100 text-wrap">
			{data.label}
		</span>
	</div>

	{#if data.meta}
		<p class="pl-1 mt-1 text-[10px] text-surface-600-400 truncate">{data.meta}</p>
	{/if}

	{#if data.assignments?.length}
		<div class="flex flex-wrap items-center gap-1 pl-1 mt-1.5">
			{#each data.assignments ?? [] as assignment}
				<span
					class="badge {style.chip} text-[9px] px-1.5 py-0.5 font-mono font-bold"
					class:opacity-60={!assignment.is_blocking}
				>
					{assignment.role_code}
				</span>
			{/each}
		</div>
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

	<Handle type="target" position={Position.Left} class={handleClass} />
	<Handle type="source" position={Position.Right} class={handleClass} />
</div>
