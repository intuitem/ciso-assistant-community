import { BASE_API_URL } from '$lib/utils/constants';
import { del, unwrap } from '$lib/utils/portalApi';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.custom_portals) redirect(302, '/');
	// FolderTreeSelect on the page fetches its own org tree, so we only need the documents.
	const docs = await fetch(`${BASE_API_URL}/public-documents/`);
	return { documents: await unwrap(docs) };
};

export const actions: Actions = {
	upload: async ({ request, fetch }) => {
		const data = await request.formData();
		const file = data.get('file');
		const name = (data.get('name') as string)?.trim();
		const folder = data.get('folder') as string;
		if (!file || !(file instanceof File) || file.size === 0)
			return fail(400, { error: 'File required' });
		if (!name) return fail(400, { error: 'Name required' });
		// Rebuild FormData — never forward the raw request stream (boundary loss).
		const body = new FormData();
		body.append('name', name);
		if (folder) body.append('folder', folder);
		body.append('file', file);
		const res = await fetch(`${BASE_API_URL}/public-documents/`, { method: 'POST', body });
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	},
	delete: async ({ request, fetch }) => {
		const id = (await request.formData()).get('id');
		const res = await del(fetch, `/public-documents/${id}/`);
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return { success: true };
	}
};
