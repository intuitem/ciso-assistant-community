import { BASE_API_URL } from '$lib/utils/constants';
import { json, type RequestHandler } from '@sveltejs/kit';

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/threat-models/${params.id}/save-graph/`, {
		method: 'POST',
		body: JSON.stringify(await request.json())
	});
	// the backend may answer with a non-JSON body (proxy error, 500 page), which
	// must not surface as an unhandled parse failure in the editor
	const payload = await res.json().catch(() => ({
		errors: [`Unexpected response from the server (${res.status}).`]
	}));
	return json(payload, { status: res.ok ? res.status : res.status || 502 });
};
