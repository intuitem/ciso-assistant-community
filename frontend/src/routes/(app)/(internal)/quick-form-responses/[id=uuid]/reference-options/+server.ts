import { BASE_API_URL } from '$lib/utils/constants';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Reviewer surface first, the requester's own as fallback — a requester holds no folder
// rights on the domain their request landed in, which is the whole reason this endpoint
// exists rather than the ordinary autocomplete.
export const GET: RequestHandler = async ({ fetch, params, url, locals }) => {
	if (!locals.user) error(401, 'Unauthorized');
	const query = `?question=${encodeURIComponent(url.searchParams.get('question') ?? '')}&search=${encodeURIComponent(
		url.searchParams.get('search') ?? ''
	)}`;
	for (const base of ['quick-form-responses', 'my-requests']) {
		const res = await fetch(`${BASE_API_URL}/${base}/${params.id}/reference-options/${query}`);
		if (res.ok) return json(await res.json());
		if (res.status !== 403 && res.status !== 404) error(res.status, 'Options unavailable');
	}
	return json({ results: [] });
};
