import { BASE_API_URL } from '$lib/utils/constants';
import { error, fail, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	// `/my-requests` authorises on respondent membership, not folder RBAC: a requester
	// holds no role on the domain their requests land in.
	//
	// Asking is deliberately NOT done here. Which requests a person can file, how they
	// are grouped and what they are called is a portal's editorial decision, and a user
	// may be entitled to several portals offering unrelated things. We only link back to
	// the portals, and only when the user can actually file something.
	// `fetch` resolves for HTTP errors, so an error body would arrive as the array.
	// Paginated routes answer with an envelope, custom actions with a bare array.
	const asList = async (res: Response) => {
		if (!res.ok) error(res.status, 'Failed to load your requests');
		const body = await res.json();
		return Array.isArray(body) ? body : (body?.results ?? []);
	};
	const [requests, publications, portals] = await Promise.all([
		fetch(`${BASE_API_URL}/my-requests/`).then(asList),
		fetch(`${BASE_API_URL}/quick-form-publications/mine/`).then(asList),
		fetch(`${BASE_API_URL}/portals/mine/`).then((r) => (r.ok ? r.json() : []))
	]).catch((e) => {
		error(e?.status ?? 500, 'Failed to load your requests');
	});
	return {
		requests,
		portals: Array.isArray(publications) && publications.length ? portals : []
	};
};

const act = async (
	fetch: typeof globalThis.fetch,
	id: string,
	path: string,
	// Only these two are meant, and only one takes a body.
	method: 'POST' | 'DELETE' = 'POST'
) => {
	const res = await fetch(`${BASE_API_URL}/my-requests/${id}/${path}`, {
		method,
		...(method === 'POST'
			? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) }
			: {})
	});
	if (!res.ok) return fail(res.status, { error: await res.text() });
	return res.status === 204 ? { deleted: true } : await res.json();
};

export const actions: Actions = {
	drop: async ({ request, fetch }) =>
		act(fetch, (await request.formData()).get('id') as string, 'drop/'),
	clone: async ({ request, fetch }) =>
		act(fetch, (await request.formData()).get('id') as string, 'clone/'),
	remove: async ({ request, fetch }) =>
		act(fetch, (await request.formData()).get('id') as string, '', 'DELETE')
};
