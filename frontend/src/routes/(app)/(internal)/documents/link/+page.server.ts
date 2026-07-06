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
		const url = String(form.get('url') ?? '').trim();
		if (!url) return fail(400, { error: m.urlRequired() });
		const folder = form.get('folder');
		if (!folder) return fail(400, { error: m.domainRequired() });

		const res = await fetch(`${BASE_API_URL}/document-containers/link/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				url,
				folder: String(folder),
				document_type: String(form.get('document_type') ?? 'policy'),
				name: String(form.get('name') ?? ''),
				locale: String(form.get('locale') ?? 'en')
			})
		});
		const data = await res.json().catch(() => null);
		if (!res.ok) {
			return fail(res.status, {
				error: (data && (data.url || data.folder || data.error)) || 'Import failed'
			});
		}
		redirect(303, `/document-containers/${data.id}/document`);
	}
};
