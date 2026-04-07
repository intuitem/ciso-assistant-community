<script lang="ts">
	import type { TreeViewNode } from './types';
	import { m } from '$paraglide/messages';

	interface Props {
		nodes: TreeViewNode[];
		expandedNodes: string[];
	}

	let { nodes, expandedNodes = $bindable([]) }: Props = $props();

	let allExpanded = $derived.by(() => {
		const allIds = getAllExpandableNodeIds(nodes);
		return allIds.length > 0 && allIds.every((id) => expandedNodes.includes(id));
	});

	function getAllExpandableNodeIds(items: TreeViewNode[]): string[] {
		const ids: string[] = [];
		for (const node of items) {
			if (node.children && node.children.length > 0) {
				ids.push(node.id);
				ids.push(...getAllExpandableNodeIds(node.children));
			}
		}
		return ids;
	}

	function toggle() {
		if (allExpanded) {
			expandedNodes = [];
		} else {
			expandedNodes = getAllExpandableNodeIds(nodes);
		}
	}
</script>

<button
	type="button"
	class="btn btn-sm preset-tonal"
	title={allExpanded ? m.collapseAll() : m.expandAll()}
	onclick={toggle}
>
	<i class="fa-solid {allExpanded ? 'fa-compress' : 'fa-expand'} text-xs"></i>
	<span class="text-xs">{allExpanded ? m.collapseAll() : m.expandAll()}</span>
</button>
