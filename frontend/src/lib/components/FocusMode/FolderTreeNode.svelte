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
	}

	let { node, sortAsc, focusId, onSelect, depth = 0 }: Props = $props();

	const sortedChildren = $derived.by(() => {
		const children = node.children ?? [];
		return sortAsc
			? [...children].sort((a, b) => a.name.localeCompare(b.name))
			: [...children].sort((a, b) => b.name.localeCompare(a.name));
	});

	const hasChildren = $derived((node.children ?? []).length > 0);
	let isExpanded = $state(false);
	const isSelected = $derived(node.uuid !== null && focusId === String(node.uuid));
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
			class="flex-1 flex items-center gap-1.5 px-1.5 py-1 text-left rounded text-sm min-w-0 transition-colors
				{isSelected
				? 'bg-indigo-100 text-indigo-700'
				: node.uuid
					? 'text-slate-700 hover:bg-indigo-50 cursor-pointer'
					: 'text-slate-400 cursor-default'}"
			title={node.name}
			onclick={(e) => {
				e.stopPropagation();
				if (node.uuid) onSelect(String(node.uuid), node.name);
			}}
			disabled={!node.uuid}
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
				<FolderTreeNode node={child} {sortAsc} {focusId} {onSelect} depth={depth + 1} />
			{/each}
		</ul>
	{/if}
</li>
