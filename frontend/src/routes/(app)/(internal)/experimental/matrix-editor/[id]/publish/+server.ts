import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/risk-matrix-drafts/${params.id}/publish/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' }
	});
	const data = await res.json();
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, data);
	}
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
