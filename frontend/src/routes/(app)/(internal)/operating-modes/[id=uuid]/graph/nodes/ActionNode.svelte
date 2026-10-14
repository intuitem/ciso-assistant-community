<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import { m } from '$paraglide/messages';
	import type { Quotation } from '$lib/utils/ebios-quotation';

	interface Props {
		id: string;
		data: {
			label: string;
			iconClass?: string;
			stage: number;
			logicOp?: 'AND' | 'OR' | null;
			assets?: string[];
			assetLabels?: string[];
			successProbability?: number;
			successProbabilityPct?: number | null;
			successProbabilityLabel?: string;
			technicalDifficulty?: number;
		};
	}

	let { id, data }: Props = $props();

	const editor = getContext<{
		deleteNode: (id: string) => void;
		toggleOperator: (id: string) => void;
		editStep: (id: string) => void;
		readonly: boolean;
		quotation: Quotation | null;
		advanced: boolean;
		probabilityLabel: (level: number) => string;
		difficultyLabel: (level: number) => string;
	}>('killChainEditor');

	const cumulative = $derived(editor?.quotation?.steps[id]);
	const hasProbability = $derived(
		(data.successProbability ?? -1) >= 0 || data.successProbabilityPct != null
	);
	const hasDifficulty = $derived(!!editor?.advanced && (data.technicalDifficulty ?? -1) >= 0);

	const STAGE_CLASSES: Record<number, { border: string; accent: string }> = {
		0: { border: 'border-pink-300', accent: 'bg-pink-400' },
		1: { border: 'border-violet-300', accent: 'bg-violet-400' },
		2: { border: 'border-orange-300', accent: 'bg-orange-400' },
		3: { border: 'border-red-300', accent: 'bg-red-400' }
	};

	const stageClass = $derived(STAGE_CLASSES[data.stage] ?? STAGE_CLASSES[1]);

	let hovered = $state(false);
	let nodeElement: HTMLDivElement | undefined = $state();

	// Lift the hovered node above its neighbours so the assets tooltip isn't hidden behind them.
	$effect(() => {
		const wrapper = nodeElement?.closest<HTMLElement>('.svelte-flow__node');
		if (!wrapper || !hovered) return;
		const zIndex = wrapper.style.zIndex;
		wrapper.style.zIndex = '1000';
		return () => (wrapper.style.zIndex = zIndex);
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	bind:this={nodeElement}
	class="action-node relative font-semibold rounded-base border-[1.5px] px-3 py-2 min-w-[140px] max-w-[180px] text-center select-none bg-surface-50-950 {stageClass.border} {cumulative?.critical
		? 'ring-2 ring-error-500 ring-offset-1 ring-offset-surface-50-950'
		: ''}"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
	ondblclick={() => {
		if (!editor?.readonly) editor?.editStep(id);
	}}
>
	{#if hovered && data.assetLabels?.length}
		<div
			class="pointer-events-none absolute left-1/2 top-full z-10 mt-2 w-max max-w-[240px] -translate-x-1/2 rounded-base border border-surface-200-800 bg-surface-50-950 px-2 py-1.5 text-left text-[10px] font-normal shadow-lg"
		>
			<p class="mb-1 font-semibold text-surface-700-300">{m.supportingAssets()}</p>
			<ul class="space-y-0.5 text-surface-900-100">
				{#each data.assetLabels as assetLabel}
					<li class="flex items-center gap-1">
						<i class="fa-solid fa-server text-[8px] text-surface-500"></i>{assetLabel}
					</li>
				{/each}
			</ul>
		</div>
	{/if}
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base {stageClass.accent}"></div>

	<div class="flex items-center gap-2">
		{#if data.iconClass}
			<i class="{data.iconClass} text-[11px] text-surface-900-100"></i>
		{/if}
		<span class="text-[11px] leading-tight text-surface-900-100 text-wrap">{data.label}</span>
	</div>
	{#if data.assets?.length || hasProbability || hasDifficulty}
		<div
			class="mt-1 flex flex-wrap items-center justify-center gap-x-2 text-[10px] text-surface-600-400"
		>
			{#if hasProbability}
				<span class="flex items-center gap-1" title={m.successProbability()}>
					<i class="fa-solid fa-dice text-[9px]"></i>
					{#if (data.successProbability ?? -1) >= 0}{data.successProbabilityLabel}{/if}
					{#if data.successProbabilityPct != null}({data.successProbabilityPct}%){/if}
				</span>
				{#if cumulative && cumulative.probability >= 0 && cumulative.probability !== data.successProbability}
					<span
						class="flex items-center gap-1 font-bold {cumulative.critical
							? 'text-error-600-400'
							: 'text-surface-700-300'}"
						title={m.cumulativeProbability()}
						data-testid="step-cumulative-probability"
					>
						<i class="fa-solid fa-arrow-right text-[9px]"></i>
						{editor.probabilityLabel(cumulative.probability)}
					</span>
				{/if}
			{/if}
			{#if hasDifficulty}
				<span class="flex items-center gap-1" title={m.technicalDifficulty()}>
					<i class="fa-solid fa-dumbbell text-[9px]"></i>
					{editor.difficultyLabel(data.technicalDifficulty ?? -1)}
				</span>
				{#if cumulative && cumulative.difficulty !== null && cumulative.difficulty >= 0 && cumulative.difficulty !== data.technicalDifficulty}
					<span
						class="flex items-center gap-1 font-bold {cumulative.critical
							? 'text-error-600-400'
							: 'text-surface-700-300'}"
						title={m.cumulativeDifficulty()}
						data-testid="step-cumulative-difficulty"
					>
						<i class="fa-solid fa-arrow-right text-[9px]"></i>
						{editor.difficultyLabel(cumulative.difficulty)}
					</span>
				{/if}
			{/if}
			{#if data.assets?.length}
				<span class="flex items-center gap-1" title={m.supportingAssets()}>
					<i class="fa-solid fa-server text-[9px]"></i>
					{data.assets.length}
				</span>
			{/if}
		</div>
	{/if}

	{#if hovered && !editor?.readonly}
		<button
			type="button"
			aria-label="Delete node"
			class="nopan nodrag absolute -top-2 -left-2 w-4 h-4 rounded-full bg-error-500 text-white text-[8px] flex items-center justify-center hover:bg-error-600 cursor-pointer"
			onclick={() => editor?.deleteNode(id)}
		>
			✕
		</button>
		<button
			type="button"
			aria-label="{m.edit()} {m.killChain()}"
			title="{m.edit()} {m.killChain()}"
			class="nopan nodrag absolute -top-2 -right-2 w-4 h-4 rounded-full bg-primary-500 text-white text-[8px] flex items-center justify-center hover:bg-primary-600 cursor-pointer"
			onclick={() => editor?.editStep(id)}
		>
			<i class="fa-solid fa-pen text-[8px]"></i>
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
