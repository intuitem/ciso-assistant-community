<script lang="ts">
	import FolderTreeNode from './FolderTreeNode.svelte';

	export interface TreeNode {
		name: string;
		uuid: string | null;
		content_type?: string;
		children?: TreeNode[];
	}

	interface Props {
		node: TreeNode;
		sortAsc: boolean;
		focusId: string | null;
		onSelect: (id: string, name: string) => void;
		depth?: number;
		contentTypes?: string[];
	}

	let {
		node,
		sortAsc,
		focusId,
		onSelect,
		depth = 0,
		contentTypes = ['DO', 'GL']
	}: Props = $props();

	const sortedChildren = $derived.by(() => {
		const children = node.children ?? [];
		return sortAsc
			? [...children].sort((a, b) => a.name.localeCompare(b.name))
			: [...children].sort((a, b) => b.name.localeCompare(a.name));
	});

	const hasChildren = $derived((node.children ?? []).length > 0);
	let isExpanded = $state(false);
	const isSelected = $derived(node.uuid !== null && focusId === String(node.uuid));
	// Node is selectable if it has a uuid
	const isSelectable = $derived(!!node.uuid);
	// Whether this node should be shown at all
	const isVisible = $derived(!node.content_type || contentTypes.includes(node.content_type));
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
				{isSelected ? 'bg-indigo-100 text-indigo-700' : 'text-slate-700 hover:bg-indigo-50 cursor-pointer'}"
				title={node.name}
				onclick={(e) => {
					e.stopPropagation();
					if (isSelectable) onSelect(String(node.uuid), node.name);
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
					/>
				{/each}
			</ul>
		{/if}
	{/if}
</li>
