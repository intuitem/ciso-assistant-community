import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';
import type { OrgTreeNode } from './tree';

// Enclaves are third-party visitor spaces, not part of the organisational structure,
// so the board never shows them.
async function fetchOrgTree(
	fetch: typeof globalThis.fetch,
	writePerm: string
): Promise<OrgTreeNode | null> {
	const params = new URLSearchParams({
		include_perimeters: 'false',
		include_enclaves: 'false',
		write_perm: writePerm
	});
	try {
		const res = await fetch(`${BASE_API_URL}/folders/org_tree/?${params}`);
		return res.ok ? await res.json() : null;
	} catch {
		return null;
	}
}

export const load: PageServerLoad = async ({ fetch }) => {
	// Two passes over org_tree. A move is allowed only when the user holds
	// change_folder on the folder being moved AND add_folder on its new parent —
	// that second half is enforced by FolderWriteSerializer.validate_parent_folder,
	// so the board mirrors the same rule instead of inventing its own.
	const [movableTree, receivingTree] = await Promise.all([
		fetchOrgTree(fetch, 'change_folder'),
		fetchOrgTree(fetch, 'add_folder')
	]);

	const createForm = await superValidate({}, zod(modelSchema('folders')), { errors: false });

	return {
		movableTree,
		receivingTree,
		folderModel: {
			...getModelInfo('folders'),
			urlModel: 'folders',
			createForm
		}
	};
};

export const actions: Actions = {
	create: async (event) => {
		return defaultWriteFormAction({
			event,
			urlModel: 'folders',
			action: 'create',
			redirectToWrittenObject: false
		});
	}
};
