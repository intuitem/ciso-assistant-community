<script lang="ts">
	import { untrack } from 'svelte';
	import FolderTreeNode from './FolderTreeNode.svelte';

	export interface TreeNode {
		name: string;
		uuid: string | null;
		content_type?: string;
		/** When false, the node exists in the tree for navigation only and cannot be selected. */
		writable?: boolean;
		children?: TreeNode[];
	}

	interface Props {
		node: TreeNode;
		sortAsc: boolean;
		focusId: string | null;
		onSelect: (id: string, name: string, path: string[]) => void;
		depth?: number;
		contentTypes?: string[];
		ancestors?: string[];
	}

	let {
		node,
		sortAsc,
		focusId,
		onSelect,
		depth = 0,
		contentTypes = ['DO', 'GL'],
		ancestors = []
	}: Props = $props();

	const sortedChildren = $derived.by(() => {
		const children = node.children ?? [];
		return sortAsc
			? [...children].sort((a, b) => a.name.localeCompare(b.name))
			: [...children].sort((a, b) => b.name.localeCompare(a.name));
	});

	const hasChildren = $derived((node.children ?? []).length > 0);

	// Returns true if `n` or any of its descendants is writable.
	function subtreeHasWritable(n: TreeNode): boolean {
		if (n.writable !== false) return true;
		return (n.children ?? []).some(subtreeHasWritable);
	}

	// Auto-expand non-writable ancestor nodes that contain writable descendants
	// Only triggers when a write_perm filter is active (node.writable === false means
	// a filter is in use and this node is an ancestor-only entry).
	// Computed once at init (untrack); user collapses afterward are respected.
	const shouldAutoExpand = untrack(
		() => node.writable === false && (node.children ?? []).some(subtreeHasWritable)
	);

	let isExpanded = $state(shouldAutoExpand);
	const isSelected = $derived(node.uuid !== null && focusId === String(node.uuid));
	// Node is selectable if it has a uuid, matches the allowed content types,
	// and — when a write_perm filter is active.
	const isSelectable = $derived(
		!!node.uuid &&
			(!node.content_type || contentTypes.includes(node.content_type)) &&
			node.writable !== false
	);
	// Whether this node should be shown at all
	const isVisible = $derived(!node.content_type || contentTypes.includes(node.content_type));

	// Auto-expand if the selected node is somewhere in this subtree
	const subtreeHasFocus = $derived.by(() => {
		if (!focusId) return false;
		function visit(n: TreeNode): boolean {
			if (n.uuid !== null && focusId === String(n.uuid)) return true;
			for (const child of n.children ?? []) {
				if (visit(child)) return true;
			}
			return false;
		}
		return visit(node);
	});

	// Track which focusId triggered the last auto-expand to avoid fighting manual collapses
	let autoExpandedFor = $state<string | null>(null);
	$effect(() => {
		if (focusId && focusId !== autoExpandedFor && subtreeHasFocus) {
			isExpanded = true;
			autoExpandedFor = focusId;
		}
	});
</script>

<li class="list-none m-0 p-0">
	{#if isVisible}
		<div class="flex items-center" style="padding-left: {Math.min(depth, 6) * 14}px">
			{#if hasChildren}
				<button
					type="button"
					onclick={(e) => {
						e.stopPropagation();
						isExpanded = !isExpanded;
					}}
					class="flex-shrink-0 w-5 h-6 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-transform duration-150 {isExpanded
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
					? 'bg-indigo-100 text-indigo-700'
					: isSelectable
						? 'text-slate-700 hover:bg-indigo-50 cursor-pointer'
						: 'text-slate-400 cursor-not-allowed'}"
				title={node.name}
				onclick={(e) => {
					e.stopPropagation();
					if (isSelectable) onSelect(String(node.uuid), node.name, ancestors);
				}}
				disabled={!isSelectable}
			>
				<i
					class="fa-solid fa-folder flex-shrink-0 text-xs {isSelected
						? 'text-indigo-500'
						: 'text-slate-400'}"
				></i>
				<span class="truncate">{node.name}</span>
				{#if isSelected}
					<i class="fa-solid fa-check ml-auto flex-shrink-0 text-indigo-500 text-xs"></i>
				{/if}
			</button>
		</div>

		{#if isExpanded && sortedChildren.length > 0}
			<ul class="list-none p-0 m-0 {depth === 5 ? 'border-l border-slate-200 ml-3' : ''}">
				{#each sortedChildren as child (child.uuid ?? child.name)}
					<FolderTreeNode
						node={child}
						{sortAsc}
						{focusId}
						{onSelect}
						{contentTypes}
						depth={depth + 1}
						ancestors={[...ancestors, node.name]}
					/>
				{/each}
			</ul>
		{/if}
	{/if}
</li>
