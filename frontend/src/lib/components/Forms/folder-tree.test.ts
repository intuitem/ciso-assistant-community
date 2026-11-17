import { describe, expect, it } from 'vitest';
import type { TreeNode } from '../FocusMode/FolderTreeNode.svelte';
import { keepOnlyEnclaveOf } from './folder-tree';

function folder(uuid: string, content_type: string, children: TreeNode[] = []): TreeNode {
	return { name: uuid, uuid, content_type, writable: true, children };
}

const tree = folder('root', 'GL', [
	folder('domain', 'DO', [
		folder('vendor-a', 'EN', [folder('vendor-a-sub', 'DO')]),
		folder('vendor-b', 'EN')
	]),
	folder('vendor-c', 'EN')
]);

function uuids(node: TreeNode | null): string[] {
	if (!node) return [];
	return [node.uuid, ...(node.children ?? []).flatMap(uuids)];
}

describe('keepOnlyEnclaveOf', () => {
	it('drops every enclave when the value is not in one', () => {
		expect(uuids(keepOnlyEnclaveOf(tree, 'domain'))).toEqual(['root', 'domain']);
		expect(uuids(keepOnlyEnclaveOf(tree, null))).toEqual(['root', 'domain']);
	});

	it('keeps the enclave holding the value, and only that one', () => {
		expect(uuids(keepOnlyEnclaveOf(tree, 'vendor-b'))).toEqual(['root', 'domain', 'vendor-b']);
		expect(uuids(keepOnlyEnclaveOf(tree, 'vendor-a-sub'))).toEqual([
			'root',
			'domain',
			'vendor-a',
			'vendor-a-sub'
		]);
	});
});
