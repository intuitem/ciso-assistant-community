<script lang="ts">
	import RingGlyph from './RingGlyph.svelte';
	import { formatPercent } from './format';
	import { visibleList } from './layout';
	import type { RingColor, RingNode } from './types';

	interface Props {
		root: RingNode;
		collapsed: Set<string>;
		only?: Set<string>;
		/** No collapse toggles (e.g. while a focus filter is on). */
		locked?: boolean;
		selectedId?: string | null;
		color: RingColor;
		labelHeader?: string;
		ownHeader?: string;
		branchHeader?: string;
		height?: string;
		onselect?: (id: string) => void;
		ontoggle?: (id: string) => void;
	}

	let {
		root,
		collapsed,
		only,
		locked = false,
		selectedId = null,
		color,
		labelHeader = '',
		ownHeader = '',
		branchHeader = '',
		height = '70vh',
		onselect,
		ontoggle
	}: Props = $props();

	const rows = $derived(visibleList(root, collapsed, only));
	const expandable = (n: RingNode) =>
		!locked && (only ? n.children.some((c) => only.has(c.id)) : n.children.length > 0);
	let container: HTMLDivElement | undefined = $state();

	export function scrollTo(id: string) {
		container
			?.querySelector(`[data-node-id="${CSS.escape(id)}"]`)
			?.scrollIntoView({ block: 'center' });
	}

	const fmt = formatPercent;
</script>

<div bind:this={container} class="overflow-auto" style="max-height: {height}" role="tree">
	<div
		class="sticky top-0 z-10 flex items-center gap-2 border-b border-surface-200-800 bg-surface-50-950 py-1 pr-3 pl-2 text-xs font-semibold tracking-wide text-surface-500 uppercase"
	>
		<span class="flex-1">{labelHeader}</span>
		<span class="w-14 text-right">{ownHeader}</span>
		<span class="w-36 text-right">{branchHeader}</span>
	</div>
	{#each rows as { node: n, depth } (n.id)}
		{@const open = !locked && !collapsed.has(n.id)}
		<div
			data-node-id={n.id}
			role="treeitem"
			aria-selected={selectedId === n.id}
			aria-expanded={expandable(n) ? open : undefined}
			tabindex="0"
			class="flex cursor-pointer items-center gap-2 py-1 pr-3 outline-none hover:bg-surface-100-900 {selectedId ===
			n.id
				? 'bg-primary-50-950 shadow-[inset_3px_0_0_var(--color-primary-500)]'
				: ''}"
			style="padding-left: {depth * 20 + 8}px"
			onclick={() => onselect?.(n.id)}
			onkeydown={(e) => e.key === 'Enter' && onselect?.(n.id)}
		>
			{#if expandable(n)}
				<button
					class="w-4 shrink-0 text-xs text-surface-500"
					aria-label={open ? 'Collapse' : 'Expand'}
					onclick={(e) => {
						e.stopPropagation();
						ontoggle?.(n.id);
					}}><i class="fa-solid {open ? 'fa-chevron-down' : 'fa-chevron-right'}"></i></button
				>
			{:else}
				<span class="w-4 shrink-0"></span>
			{/if}
			<svg width="28" height="28" viewBox="-14 -14 28 28" class="shrink-0">
				<RingGlyph
					own={n.own}
					faint={n.faint}
					ownSegments={n.ownSegments}
					branch={n.branch}
					showBranch={n.showBranch}
					empty={n.empty}
					{color}
					rOut={12}
					rIn={6.5}
					wOut={2.5}
					wIn={4}
				/>
			</svg>
			{#if n.badge}
				<span class="rounded bg-primary-100-900 px-1.5 text-xs font-semibold text-primary-800-200"
					>{n.badge}</span
				>
			{/if}
			<div class="min-w-0 flex-1">
				<div class="truncate text-sm font-medium {n.muted ? 'text-surface-500 italic' : ''}">
					{n.label}
					{#if collapsed.has(n.id) && !locked && n.hiddenCount}
						<span class="text-xs font-normal text-surface-500">+{n.hiddenCount}</span>
					{/if}
				</div>
				{#if n.sublabel}
					<div class="truncate text-xs text-surface-500">
						{n.sublabel}{#if n.warning}<span class="text-warning-700-300"> · {n.warning}</span>{/if}
					</div>
				{/if}
			</div>
			<span
				class="w-14 text-right text-sm font-semibold"
				style="color: {color(n.own ?? null)}"
				title={n.warningDetail}
				><span class:opacity-50={n.faint}
					>{n.own !== undefined ? (n.ownLabel ?? fmt(n.own)) : ''}</span
				>{#if n.warning}<span class="ml-0.5 text-xs text-warning-500">◔</span>{/if}</span
			>
			<span class="flex w-36 items-center justify-end gap-2">
				{#if n.showBranch !== false}
					<span class="h-1.5 w-20 overflow-hidden rounded-full bg-surface-200-800">
						<span
							class="block h-full"
							style="width: {n.branch ?? 0}%; background: {color(n.branch)}"
						></span>
					</span>
					<span class="w-10 text-right text-xs">{fmt(n.branch)}</span>
				{/if}
			</span>
		</div>
	{/each}
</div>
