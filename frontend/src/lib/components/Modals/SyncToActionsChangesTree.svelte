<script lang="ts">
	import { m } from '$paraglide/messages';
	import SyncToActionsChangesTreeItem, {
		type SyncToActionsFieldChange,
		type SyncToActionsTreeNode
	} from './SyncToActionsChangesTreeItem.svelte';

	interface RequirementPathSegment {
		id?: string;
		urn?: string;
		label?: string;
	}

	interface SyncToActionsChange {
		str?: string;
		requirement?: {
			path?: RequirementPathSegment[];
		};
		changes?: SyncToActionsFieldChange[];
	}

	interface Props {
		changes: Record<string, SyncToActionsChange> | SyncToActionsChange[];
		message?: string;
	}

	let { changes, message = '' }: Props = $props();

	function getOrCreateNode(
		siblings: SyncToActionsTreeNode[],
		key: string,
		label: string
	): SyncToActionsTreeNode {
		let node = siblings.find((candidate) => candidate.key === key);
		if (!node) {
			node = { key, label, children: [], changes: [], syncCount: 0 };
			siblings.push(node);
		}
		return node;
	}

	function countSyncItems(
		input: Record<string, SyncToActionsChange> | SyncToActionsChange[]
	): number {
		const items = Array.isArray(input) ? input : Object.values(input ?? {});
		return items.filter((item) => (item.changes ?? []).length > 0).length;
	}

	function updateSyncCounts(nodes: SyncToActionsTreeNode[]): number {
		let total = 0;
		for (const node of nodes) {
			const childrenCount = updateSyncCounts(node.children);
			node.syncCount = childrenCount;
			total += childrenCount + (node.changes.length > 0 ? 1 : 0);
		}
		return total;
	}

	function buildTree(
		input: Record<string, SyncToActionsChange> | SyncToActionsChange[]
	): SyncToActionsTreeNode[] {
		const items = Array.isArray(input) ? input : Object.values(input ?? {});
		const roots: SyncToActionsTreeNode[] = [];

		for (const item of items) {
			const path = item.requirement?.path?.filter((segment) => segment?.label) ?? [];
			const normalizedPath =
				path.length > 0
					? path
					: [{ id: item.str ?? 'unknown', label: item.str ?? 'Unknown requirement' }];
			let siblings = roots;
			let currentNode: SyncToActionsTreeNode | undefined;
			let parentKey = '';

			for (const segment of normalizedPath) {
				const label = segment.label ?? segment.id ?? segment.urn ?? 'Unknown requirement';
				const key = segment.urn || segment.id || `${parentKey}/${label}`;
				currentNode = getOrCreateNode(siblings, key, label);
				siblings = currentNode.children;
				parentKey = key;
			}

			if (currentNode) {
				currentNode.changes.push(...(item.changes ?? []));
			}
		}

		updateSyncCounts(roots);
		return roots;
	}

	const tree = $derived(buildTree(changes));
	const syncItemsCount = $derived(countSyncItems(changes));
</script>

<article>
	{#if message}
		<p
			class="sticky top-0 z-10 flex items-center justify-between gap-3 bg-surface-100 bg-opacity-80 p-2 backdrop-blur-xs"
		>
			<span>{message}</span>
			<span class="rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
				{syncItemsCount} {m.items()}
			</span>
		</p>
	{/if}

	{#if tree.length > 0}
		<ul class="space-y-1 p-2">
			{#each tree as node (node.key)}
				<SyncToActionsChangesTreeItem {node} />
			{/each}
		</ul>
	{:else}
		<p class="p-2 text-sm text-gray-500">No changes.</p>
	{/if}
</article>
