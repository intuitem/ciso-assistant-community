import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import { error, fail, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	// Ordinary folder-scoped RBAC: reviewers are privileged users by construction, so
	// this is the plain list endpoint. Drafts are filtered out in the page — a request
	// nobody has submitted is not in anyone's queue.
	const [responses, actors] = await Promise.all([
		fetchAllPages(fetch, `${BASE_API_URL}/quick-form-responses/`),
		fetchAllPages(fetch, `${BASE_API_URL}/actors/?is_third_party=false`).catch(() => [])
	]).catch((e) => {
		error(e?.status ?? 500, 'Failed to load the request queue');
	});
	return { responses, actors };
};

export const actions: Actions = {
	setStatus: async ({ request, fetch }) => {
		const data = await request.formData();
		const res = await fetch(`${BASE_API_URL}/quick-form-responses/${data.get('id')}/set-status/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				status: data.get('status'),
				resolution: data.get('resolution') || undefined
			})
		});
		if (!res.ok) return fail(res.status, { error: await res.text() });
		return await res.json();
	}
};
