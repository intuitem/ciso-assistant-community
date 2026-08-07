<script lang="ts">
	import TreeSelectNode from './TreeSelectNode.svelte';

	export interface TreeSelectItem {
		id: string;
		label: string;
		/** False renders the node as a non-selectable grouping row. */
		selectable: boolean;
		children: TreeSelectItem[];
	}

	interface Props {
		node: TreeSelectItem;
		sortAsc: boolean;
		selectedId: string | null;
		onSelect: (id: string, label: string, path: string[]) => void;
		icon: string;
		depth?: number;
		ancestors?: string[];
	}

	let { node, sortAsc, selectedId, onSelect, icon, depth = 0, ancestors = [] }: Props = $props();

	const sortedChildren = $derived.by(() => {
		const children = node.children ?? [];
		return sortAsc
			? [...children].sort((a, b) => a.label.localeCompare(b.label))
			: [...children].sort((a, b) => b.label.localeCompare(a.label));
	});

	const hasChildren = $derived((node.children ?? []).length > 0);
	const isSelected = $derived(selectedId === String(node.id));

	const subtreeHasSelection = $derived.by(() => {
		if (!selectedId) return false;
		function visit(n: TreeSelectItem): boolean {
			if (selectedId === String(n.id)) return true;
			return (n.children ?? []).some(visit);
		}
		return visit(node);
	});

	// A non-selectable node only exists to carry its children.
	let isExpanded = $state(!node.selectable && hasChildren);

	// Tracked so manual collapses stick.
	let autoExpandedFor = $state<string | null>(null);
	$effect(() => {
		if (selectedId && selectedId !== autoExpandedFor && subtreeHasSelection) {
			isExpanded = true;
			autoExpandedFor = selectedId;
		}
	});
</script>

<li class="list-none m-0 p-0">
	<div class="flex items-center" style="padding-left: {Math.min(depth, 6) * 14}px">
		{#if hasChildren}
			<button
				type="button"
				onclick={(e) => {
					e.stopPropagation();
					isExpanded = !isExpanded;
				}}
				class="flex-shrink-0 w-5 h-6 flex items-center justify-center text-surface-500 hover:text-surface-600-400 transition-transform duration-150 {isExpanded
					? 'rotate-90'
					: ''}"
			>
				<i class="fa-solid fa-chevron-right text-[9px]"></i>
			</button>
		{:else}
			<span class="w-5 flex-shrink-0"></span>
		{/if}

		<button
			type="button"
			role="option"
			aria-selected={isSelected}
			class="flex-1 flex items-center gap-1.5 px-1.5 py-1 text-left rounded text-sm min-w-0 transition-colors
			{isSelected
				? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300'
				: node.selectable
					? 'text-surface-700-300 hover:bg-indigo-50 dark:hover:bg-indigo-950 cursor-pointer'
					: 'text-surface-500 cursor-not-allowed'}"
			title={node.label}
			onclick={(e) => {
				e.stopPropagation();
				if (node.selectable) onSelect(String(node.id), node.label, ancestors);
			}}
			disabled={!node.selectable}
		>
			<i class="{icon} flex-shrink-0 text-xs {isSelected ? 'text-indigo-500' : 'text-surface-500'}"
			></i>
			<span class="truncate">{node.label}</span>
			{#if isSelected}
				<i class="fa-solid fa-check ml-auto flex-shrink-0 text-indigo-500 text-xs"></i>
			{/if}
		</button>
	</div>

	{#if isExpanded && sortedChildren.length > 0}
		<ul class="list-none p-0 m-0 {depth === 5 ? 'border-l border-surface-200-800 ml-3' : ''}">
			{#each sortedChildren as child (child.id)}
				<TreeSelectNode
					node={child}
					{sortAsc}
					{selectedId}
					{onSelect}
					{icon}
					depth={depth + 1}
					ancestors={[...ancestors, node.label]}
				/>
			{/each}
		</ul>
	{/if}
</li>
