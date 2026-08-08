<script lang="ts">
	import { m } from '$paraglide/messages';
	import { Handle, Position, useUpdateNodeInternals } from '@xyflow/svelte';
	import { getContext } from 'svelte';

	interface Branch {
		branchId: string;
		name: string;
		isDefault: boolean;
		wired: boolean;
	}

	interface Props {
		id: string;
		selected?: boolean;
		data: {
			nodeType: 'condition';
			label: string;
			meta?: string | null;
			branches?: Branch[];
			error?: string | null;
			runState?: 'visited' | 'active' | 'error' | null;
		};
	}

	let { id, selected = false, data }: Props = $props();

	const editor = getContext<{
		readonly: boolean;
		deleteNode: (id: string) => void;
		addBranch: (id: string) => void;
	}>('workflowEditor');

	let hovered = $state(false);
	function handleClass(wired: boolean) {
		if (editor?.readonly) return '!w-0 !h-0 !border-0 !bg-transparent !pointer-events-none';
		// Unwired ports read as "open" (dashed, muted) so it's clear they still
		// need a wire; wired ports are solid.
		// Larger hit area than the default 12px dot: these ports are the primary
		// wiring affordance and were easy to miss (grabbing the node instead).
		return wired
			? '!w-4 !h-4 !bg-surface-50-950 !border-2 !border-surface-600-400'
			: '!w-4 !h-4 !bg-transparent !border-2 !border-dashed !border-surface-400-600 hover:!border-primary-500 hover:!bg-primary-500/10';
	}

	// Branches (and thus ports) are added/removed/reordered as node data changes;
	// tell Svelte Flow to re-measure so edges anchor to the fresh handles.
	const updateNodeInternals = useUpdateNodeInternals();
	$effect(() => {
		void (data.branches ?? []).map((branch) => branch.branchId).join('|');
		updateNodeInternals(id);
	});

	const conditionalBranches = $derived((data.branches ?? []).filter((b) => !b.isDefault));
	const defaultBranch = $derived((data.branches ?? []).find((b) => b.isDefault) ?? null);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="condition-node relative rounded-base border-[1.5px] bg-surface-50-950 py-2 w-[200px] select-none transition-shadow
	border-warning-300 dark:border-warning-700
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
	data-testid="workflow-node-condition"
>
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base bg-warning-500"></div>

	<div class="flex items-center gap-2 pl-4 pr-3">
		<i class="fa-solid fa-code-branch text-xs text-surface-700-300"></i>
		<span class="text-xs font-semibold leading-tight text-surface-900-100 text-wrap">
			{data.label}
		</span>
	</div>

	{#if data.meta}
		<p class="pl-4 pr-3 mt-1 text-[10px] text-surface-600-400 truncate">{data.meta}</p>
	{/if}

	<div class="mt-1.5 space-y-0.5">
		{#each conditionalBranches as branch, index (branch.branchId)}
			<div
				class="nodrag relative flex items-center justify-end min-h-[22px] pl-4 pr-3 py-0.5"
				data-testid="condition-branch-row"
				title={branch.wired ? undefined : m.branchUnwired()}
			>
				<span
					class="text-[10px] leading-tight truncate {branch.name
						? 'text-surface-700-300'
						: 'italic text-surface-500'} {branch.wired ? '' : 'opacity-70'}"
				>
					{branch.name || m.branchDefaultName({ number: index + 1 })}
				</span>
				<Handle
					id={branch.branchId}
					type="source"
					position={Position.Right}
					isConnectable={!editor?.readonly && !branch.wired}
					class={handleClass(branch.wired)}
				/>
			</div>
		{/each}
		{#if !editor?.readonly}
			<div
				class="relative flex items-center justify-end min-h-[20px] pl-4 pr-3 py-0.5"
				data-testid="condition-add-branch-row"
			>
				<button
					type="button"
					class="nopan nodrag text-[10px] leading-tight text-surface-500 border border-dashed border-surface-400-600 rounded px-1.5 py-0.5 hover:text-primary-500 hover:border-primary-500 cursor-pointer"
					onclick={(e) => {
						e.stopPropagation();
						editor?.addBranch(id);
					}}
					data-testid="condition-add-branch"
				>
					<i class="fa-solid fa-plus mr-0.5"></i>{m.addBranch()}
				</button>
			</div>
		{/if}
		<!-- Default (otherwise) output: always present, evaluated last, muted and
		     neutral (not the warning accent of the conditional rows above). -->
		{#if defaultBranch}
			<div
				class="nodrag relative flex items-center justify-end min-h-[22px] pl-4 pr-3 py-0.5 mt-1 pt-1 border-t border-surface-200-800"
				data-testid="condition-default-row"
				title={defaultBranch.wired ? undefined : m.branchUnwired()}
			>
				<span
					class="text-[10px] leading-tight truncate {defaultBranch.name
						? 'text-surface-600-400'
						: 'italic text-surface-500'} {defaultBranch.wired ? '' : 'opacity-70'}"
				>
					{defaultBranch.name || m.branchOtherwise()}
				</span>
				<Handle
					id={defaultBranch.branchId}
					type="source"
					position={Position.Right}
					isConnectable={!editor?.readonly && !defaultBranch.wired}
					class={handleClass(defaultBranch.wired)}
				/>
			</div>
		{/if}
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

	<Handle type="target" position={Position.Left} class={handleClass(true)} />
</div>
