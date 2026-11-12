import { BASE_API_URL } from '#lib/utils/constants.js';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const UUID = /^[0-9a-f-]{36}$/i;

// `/requirement-assessments/{id}` resolves to the detail page, not the generic
// JSON proxy, so the review panel reads requirement context through here.
export const GET: RequestHandler = async ({ fetch, url }) => {
	const ids = (url.searchParams.get('ids') ?? '').split(',').filter((id) => UUID.test(id));
	const found = await Promise.all(
		ids.slice(0, 8).map((id) =>
			fetch(`${BASE_API_URL}/requirement-assessments/${id}/`)
				.then((r) => (r.ok ? r.json() : undefined))
				.catch(() => undefined)
		)
	);
	return json(found.filter(Boolean));
};
