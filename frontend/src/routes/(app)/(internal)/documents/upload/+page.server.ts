import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (locals.featureflags?.document_management === false) {
		redirect(302, '/');
	}
	const res = await fetch(`${BASE_API_URL}/folders/?content_type=DO&content_type=GL`);
	const json = res.ok ? await res.json() : {};
	const raw: any[] = json.results ?? (Array.isArray(json) ? json : []);
	const folders = raw.map((f) => ({ id: f.id, name: f.str ?? f.name }));
	return { folders };
};

export const actions: Actions = {
	default: async ({ request, fetch }) => {
		const form = await request.formData();
		const file = form.get('file') as File | null;
		if (!file || file.size === 0) return fail(400, { error: 'A file is required.' });
		const folder = form.get('folder');
		if (!folder) return fail(400, { error: 'A domain is required.' });

		// Rebuild FormData with a concrete Blob so fetch serialises it correctly.
		const bytes = new Uint8Array(await file.arrayBuffer());
		const outgoing = new FormData();
		outgoing.append('file', new Blob([bytes], { type: file.type }), file.name);
		outgoing.append('folder', String(folder));
		outgoing.append('document_type', String(form.get('document_type') ?? 'policy'));
		outgoing.append('name', String(form.get('name') ?? ''));
		outgoing.append('locale', String(form.get('locale') ?? 'en'));

		const res = await fetch(`${BASE_API_URL}/document-containers/upload/`, {
			method: 'POST',
			body: outgoing
		});
		if (!res.ok) {
			return fail(res.status, { error: await res.text() });
		}
		redirect(303, '/documents');
	}
};
