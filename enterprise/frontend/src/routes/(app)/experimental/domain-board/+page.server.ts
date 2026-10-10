import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { modelSchema } from '$lib/utils/schemas';
import { defaultWriteFormAction } from '$lib/utils/actions';
import { superValidate } from 'sveltekit-superforms';
import { zod4 as zod } from 'sveltekit-superforms/adapters';
import type { Actions, PageServerLoad } from './$types';
import type { OrgTreeNode } from './tree';

// Enclaves are third-party visitor spaces, not org structure.
async function fetchOrgTree(
	fetch: typeof globalThis.fetch,
	writePerm: string
): Promise<OrgTreeNode | null> {
	const params = new URLSearchParams({
		include_perimeters: 'false',
		include_enclaves: 'false',
		// Decides whether a domain is an empty leaf, the only thing deletable here.
		with_counts: 'true',
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
	// A move needs change_folder on the folder and add_folder on its new parent; the
	// serializer enforces the second half, so the board mirrors the same rule.
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
