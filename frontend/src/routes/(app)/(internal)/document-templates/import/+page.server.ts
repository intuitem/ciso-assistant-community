import { BASE_API_URL } from '$lib/utils/constants';
import { fail, redirect } from '@sveltejs/kit';
import { m } from '$paraglide/messages';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.document_management) redirect(302, '/');
	const res = await fetch(`${BASE_API_URL}/folders/?content_type=DO&content_type=GL`);
	const json = res.ok ? await res.json() : {};
	const raw: any[] = json.results ?? (Array.isArray(json) ? json : []);
	const folders = raw.map((f) => ({ id: f.id, name: f.str ?? f.name }));
	return { folders };
};

export const actions: Actions = {
	default: async ({ request, fetch, locals }) => {
		if (!locals.featureflags?.document_management) redirect(302, '/');
		const form = await request.formData();
		const file = form.get('file') as File | null;
		if (!file || file.size === 0) return fail(400, { error: m.zipFileRequired() });
		const folder = form.get('folder');
		if (!folder) return fail(400, { error: m.domainRequired() });

		// Rebuild FormData with a concrete Blob so fetch serialises it correctly.
		const bytes = new Uint8Array(await file.arrayBuffer());
		const outgoing = new FormData();
		outgoing.append('file', new Blob([bytes], { type: file.type || 'application/zip' }), file.name);
		outgoing.append('folder', String(folder));

		const res = await fetch(`${BASE_API_URL}/document-templates/import/`, {
			method: 'POST',
			body: outgoing
		});
		const data = await res.json().catch(() => null);
		if (!res.ok) {
			return fail(res.status, { error: (data && (data.file || data.error)) || 'Import failed' });
		}
		return { result: data };
	}
};
