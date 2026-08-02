import { BASE_API_URL } from '$lib/utils/constants';
import { json, type RequestHandler } from '@sveltejs/kit';

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/threat-models/${params.id}/save-graph/`, {
		method: 'POST',
		body: JSON.stringify(await request.json())
	});
	return json(await res.json(), { status: res.status });
};
