import type { TreeNode } from '../FocusMode/FolderTreeNode.svelte';

/**
 * Drop every third-party workspace (enclave) from an org tree, except the one holding
 * *keepId*: an object already filed there keeps its folder in the picker, and nothing
 * else is offered.
 */
export function keepOnlyEnclaveOf(
	node: TreeNode,
	keepId: string | null | undefined
): TreeNode | null {
	const keep = keepId ? String(keepId) : null;
	const holds = (n: TreeNode): boolean => String(n.uuid) === keep || (n.children ?? []).some(holds);
	if (node.content_type === 'EN' && !(keep && holds(node))) return null;
	if (!node.children) return node;
	return {
		...node,
		children: node.children
			.map((c) => keepOnlyEnclaveOf(c, keep))
			.filter((c): c is TreeNode => c !== null)
	};
}
