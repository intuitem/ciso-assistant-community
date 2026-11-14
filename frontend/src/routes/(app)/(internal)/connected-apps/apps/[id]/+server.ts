import { BASE_API_URL } from '#lib/utils/constants.js';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(
		`${BASE_API_URL}/iam/connected-apps/apps/${encodeURIComponent(params.id)}/`
	);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.text());
	}
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
